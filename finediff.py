# -*- coding: utf-8 -*-
# Based on http://www.raymondhill.net/finediff/



def _strcspn(text, mask, start=0):
    for i in range(start, len(text)):
        if text[i] in mask:
            return i - start
    return len(text) - start

def _strspn(text, mask, start=0):
    for i in range(start, len(text)):
        if text[i] not in mask:
            return i - start
    return len(text) - start



class FineDiffOp:
    def getFromLen(self): pass
    def getToLen(self): pass
    def getOpcode(self): pass

class FineDiffDeleteOp(FineDiffOp):
    def __init__(self, length): self.fromLen = length
    def getFromLen(self): return self.fromLen
    def getToLen(self): return 0
    def getOpcode(self): return 'd' if self.fromLen == 1 else 'd%d' % self.fromLen

class FineDiffInsertOp(FineDiffOp):
    def __init__(self, text): self.text = text
    def getFromLen(self): return 0
    def getToLen(self): return len(self.text)
    def getText(self): return self.text
    def getOpcode(self): return 'i:%s' % self.text if len(self.text) == 1 else 'i%d:%s' % (len(self.text), self.text)

class FineDiffReplaceOp(FineDiffOp):
    def __init__(self, fromLen, text):
        self.fromLen = fromLen
        self.text = text
    def getFromLen(self): return self.fromLen
    def getToLen(self): return len(self.text)
    def getText(self): return self.text
    def getOpcode(self):
        result = 'd' if self.fromLen == 1 else 'd%d' % self.fromLen
        result += 'i' if len(self.text) == 1 else 'i%d' % len(self.text)
        result += ':' + self.text
        return result

class FineDiffCopyOp(FineDiffOp):
    def __init__(self, length): self.length = length
    def getFromLen(self): return self.length
    def getToLen(self): return self.length
    def getOpcode(self): return 'c' if self.length == 1 else 'c%d' % self.length
    def increase(self, size):
        self.length += size
        return self.length

class FineDiffOps:
    def __init__(self): self.edits = []
    def appendOpcode(self, opcode, from_, from_offset, from_len):
        if opcode == 'c':
            self.edits.append(FineDiffCopyOp(from_len))
        elif opcode == 'd':
            self.edits.append(FineDiffDeleteOp(from_len))
        else: # elif opcode == 'i':
            self.edits.append(FineDiffInsertOp(from_[from_offset : from_offset + from_len]))


class FineDiff:
    paragraphDelimiters = '\n\r'
    sentenceDelimiters = '.\n\r'
    wordDelimiters = ' \t.\n\r'
    characterDelimiters = ''
    paragraphGranularity = [paragraphDelimiters]
    sentenceGranularity = [paragraphDelimiters, sentenceDelimiters]
    wordGranularity = [paragraphDelimiters, sentenceDelimiters, wordDelimiters]
    characterGranularity = [paragraphDelimiters, sentenceDelimiters, wordDelimiters, characterDelimiters]
    textStack = ['.', ' \t.\n\r', '']

    def __init__(self, from_text='', to_text='', granularityStack=None):
        self.granularityStack = granularityStack if granularityStack else FineDiff.characterGranularity
        self.edits = []
        self.from_text = from_text
        self.doDiff(from_text, to_text)
    def getOps(self): return self.edits
    def getOpcodes(self): return ''.join([edit.getOpcode() for edit in self.edits])
    def renderDiffToHTML(self):
        in_offset = 0
        result = []
        for edit in self.edits:
            n = edit.getFromLen()
            if isinstance(edit, FineDiffCopyOp):
                result.append(self.renderDiffToHTMLFromOpcode('c', self.from_text, in_offset, n))
            elif isinstance(edit, FineDiffDeleteOp):
                result.append(self.renderDiffToHTMLFromOpcode('d', self.from_text, in_offset, n))
            elif isinstance(edit, FineDiffInsertOp):
                result.append(self.renderDiffToHTMLFromOpcode('i', edit.getText(), 0, edit.getToLen()))
            else: # elif isinstance(edit, FineDiffReplaceOp):
                result.append(self.renderDiffToHTMLFromOpcode('d', self.from_text, in_offset, n))
                result.append(self.renderDiffToHTMLFromOpcode('i', edit.getText(), 0, edit.getToLen()))
            in_offset += n
        return ''.join(result)
    @staticmethod
    def getDiffOpcodes(from_, to, granularities):
        return FineDiff(from_, to, granularities).getOpcodes()
    @staticmethod
    def getDiffOpsFromOpcodes(opcodes):
        diffops = FineDiffOps()
        for args in FineDiff.renderFromOpcodes(None, opcodes):
            diffops.appendOpcode(*args)
        return diffops.edits
    @staticmethod
    def renderToTextFromOpcodes(from_, opcodes):
        result = []
        for args in FineDiff.renderFromOpcodes(from_, opcodes):
            result.append(FineDiff.renderToTextFromOpcode(*args))
        return ''.join(result)
    @staticmethod
    def renderDiffToHTMLFromOpcodes(from_, opcodes):
        result = []
        for args in FineDiff.renderFromOpcodes(from_, opcodes):
            result.append(FineDiff.renderDiffToHTMLFromOpcode(*args))
        return ''.join(result)
    @staticmethod
    def renderFromOpcodes(from_, opcodes):
        opcodes_len = len(opcodes)
        from_offset = 0
        opcodes_offset = 0
        while opcodes_offset < opcodes_len:
            opcode = opcodes[opcodes_offset : opcodes_offset + 1]
            opcodes_offset += 1
            match = re.match(r'\d+', opcodes[opcodes_offset:])
            n = int(match.group()) if match else 1
            if n > 1: opcodes_offset += len(str(n))
            if opcode == 'c':
                yield ('c', from_, from_offset, n, '')
                from_offset += n
            elif opcode == 'd':
                yield ('d', from_, from_offset, n, '')
                from_offset += n
            else: # elif opcode == 'i':
                yield ('i', opcodes, opcodes_offset + 1, n)
                opcodes_offset += 1 + n

    def doDiff(self, from_text, to_text):
        self.last_edit = False
        self.stackpointer = 0
        self.from_text = from_text
        self.from_offset = 0
        if not self.granularityStack:
            return
        self._processGranularity(from_text, to_text)

    def _processGranularity(self, from_segment, to_segment):
        delimiters = self.granularityStack[self.stackpointer]
        self.stackpointer += 1
        has_next_stage = self.stackpointer < len(self.granularityStack)
        for fragment_edit in FineDiff.doFragmentDiff(from_segment, to_segment, delimiters):
            if isinstance(fragment_edit, FineDiffReplaceOp) and has_next_stage:
                self._processGranularity(self.from_text[self.from_offset : self.from_offset + fragment_edit.getFromLen()], fragment_edit.getText())
            elif isinstance(fragment_edit, FineDiffCopyOp) and isinstance(self.last_edit, FineDiffCopyOp):
                self.edits[len(self.edits) - 1].increase(fragment_edit.getFromLen())
                self.from_offset += fragment_edit.getFromLen()
            else: # elif type(fragment_edit) in [FineDiffCopyOp, FineDiffDeleteOp, FineDiffInsertOp]:
                self.last_edit = fragment_edit
                self.edits.append(fragment_edit)
                self.from_offset += fragment_edit.getFromLen()
        self.stackpointer -= 1

    @staticmethod
    def doFragmentDiff(from_text, to_text, delimiters):
        if not delimiters:
            return FineDiff.doCharDiff(from_text, to_text)
        result = {}
        from_text_len = len(from_text)
        to_text_len = len(to_text)
        from_fragments = FineDiff.extractFragments(from_text, delimiters)
        to_fragments = FineDiff.extractFragments(to_text, delimiters)
        jobs = [[0, from_text_len, 0, to_text_len]]
        cached_array_keys = {}
        while jobs:
            job = jobs.pop()
            from_segment_start, from_segment_end, to_segment_start, to_segment_end = job
            from_segment_length = from_segment_end - from_segment_start
            to_segment_length = to_segment_end - to_segment_start
            if not from_segment_length or not to_segment_length:
                if from_segment_length:
                    result[from_segment_start * 4] = FineDiffDeleteOp(from_segment_length)
                elif to_segment_length:
                    result[from_segment_start * 4] = FineDiffInsertOp(to_text[to_segment_start : to_segment_start + to_segment_length])
                continue

            best_copy_length = 0
            from_base_fragment_index = from_segment_start
            cached_array_keys_for_current_segment = {}
            while from_base_fragment_index < from_segment_end:
                from_base_fragment = from_fragments[from_base_fragment_index]
                from_base_fragment_length = len(from_base_fragment)
                if from_base_fragment not in cached_array_keys_for_current_segment:
                    if from_base_fragment not in cached_array_keys:
                        cached_array_keys[from_base_fragment] = [k for k in to_fragments.keys() if to_fragments[k] == from_base_fragment]
                        to_all_fragment_indices = cached_array_keys[from_base_fragment]
                    else:
                        to_all_fragment_indices = cached_array_keys[from_base_fragment]
                    if to_segment_start > 0 or to_segment_end < to_text_len:
                        to_fragment_indices = []
                        for to_fragment_index in to_all_fragment_indices:
                            if to_fragment_index < to_segment_start:
                                continue
                            if to_fragment_index >= to_segment_end:
                                break
                            to_fragment_indices.append(to_fragment_index)
                        cached_array_keys_for_current_segment[from_base_fragment] = to_fragment_indices
                    else:
                        to_fragment_indices = to_all_fragment_indices
                else:
                    to_fragment_indices = cached_array_keys_for_current_segment[from_base_fragment]
                for to_base_fragment_index in to_fragment_indices:
                    fragment_index_offset = from_base_fragment_length
                    while True:
                        fragment_from_index = from_base_fragment_index + fragment_index_offset
                        if fragment_from_index >= from_segment_end:
                            break
                        fragment_to_index = to_base_fragment_index + fragment_index_offset
                        if fragment_to_index >= to_segment_end:
                            break
                        if from_fragments[fragment_from_index] != to_fragments[fragment_to_index]:
                            break
                        fragment_length = len(from_fragments[fragment_from_index])
                        fragment_index_offset += fragment_length
                    if fragment_index_offset > best_copy_length:
                        best_copy_length = fragment_index_offset
                        best_from_start = from_base_fragment_index
                        best_to_start = to_base_fragment_index
                from_base_fragment_index += len(from_base_fragment)
                if best_copy_length >= from_segment_length / 2:
                    break
                if from_base_fragment_index + best_copy_length >= from_segment_end:
                    break
            if best_copy_length:
                jobs.append([from_segment_start, best_from_start, to_segment_start, best_to_start])
                result[best_from_start * 4 + 2] = FineDiffCopyOp(best_copy_length)
                jobs.append([best_from_start + best_copy_length, from_segment_end, best_to_start + best_copy_length, to_segment_end])
            else:
                result[from_segment_start * 4] = FineDiffReplaceOp(from_segment_length, to_text[to_segment_start : to_segment_start + to_segment_length])
        result = [v for k, v in sorted(result.items())]
        return result

    @staticmethod
    def doCharDiff(from_text, to_text):
        result = {}
        jobs = [[0, len(from_text), 0, len(to_text)]]
        while jobs:
            job = jobs.pop()
            from_segment_start, from_segment_end, to_segment_start, to_segment_end = job
            from_segment_len = from_segment_end - from_segment_start
            to_segment_len = to_segment_end - to_segment_start
            if not from_segment_len or not to_segment_len:
                if from_segment_len:
                    result[from_segment_start * 4 + 0] = FineDiffDeleteOp(from_segment_len)
                elif to_segment_len:
                    result[from_segment_start * 4 + 1] = FineDiffInsertOp(to_text[to_segment_start : to_segment_start + to_segment_len])
                continue
            break2 = False
            if from_segment_len >= to_segment_len:
                copy_len = to_segment_len
                while copy_len:
                    to_copy_start = to_segment_start
                    to_copy_start_max = to_segment_end - copy_len
                    while to_copy_start <= to_copy_start_max:
                        from_copy_start = from_text[from_segment_start : from_segment_start + from_segment_len].find(to_text[to_copy_start : to_copy_start + copy_len])
                        if from_copy_start != -1:
                            from_copy_start += from_segment_start
                            break2 = True
                            break
                        to_copy_start += 1
                    if break2:
                        break
                    copy_len -= 1
            else:
                copy_len = from_segment_len
                while copy_len:
                    from_copy_start = from_segment_start
                    from_copy_start_max = from_segment_end - copy_len
                    while from_copy_start <= from_copy_start_max:
                        to_copy_start = to_text[to_segment_start : to_segment_start + to_segment_len].find(from_text[from_copy_start : from_copy_start + copy_len])
                        if to_copy_start != -1:
                            to_copy_start += to_segment_start
                            break2 = True
                            break
                        from_copy_start += 1
                    if break2:
                        break
                    copy_len -= 1
            if copy_len:
                jobs.append([from_segment_start, from_copy_start, to_segment_start, to_copy_start])
                result[from_copy_start * 4 + 2] = FineDiffCopyOp(copy_len)
                jobs.append([from_copy_start + copy_len, from_segment_end, to_copy_start + copy_len, to_segment_end])
            else:
                result[from_segment_start * 4] = FineDiffReplaceOp(from_segment_len, to_text[to_segment_start : to_segment_start + to_segment_len])
        result = [v for k, v in sorted(result.items())]
        return result

    @staticmethod
    def extractFragments(text, delimiters):
        if not delimiters:
            chars = list(text) + ['']
            return chars
        fragments = {}
        start = 0
        end = 0
        while True:
            end += _strcspn(text, delimiters, end)
            end += _strspn(text, delimiters, end)
            if end == start:
                break
            fragments[start] = text[start : end]
            start = end
        fragments[start] = ''
        return fragments

    @staticmethod
    def renderToTextFromOpcode(opcode, from_, from_offset, from_len):
        if opcode in 'ci':
            return from_[from_offset : from_offset + from_len]
        return ''

    @staticmethod
    def renderDiffToHTMLFromOpcode(opcode, from_, from_offset, from_len):
        import sys
        if sys.version_info.major == 2:
            import cgi
        elif sys.version_info.major == 3:
            import html as cgi
        if opcode == 'c':
            return cgi.escape(from_[from_offset : from_offset + from_len])
        elif opcode == 'd':
            deletion = from_[from_offset : from_offset + from_len]
            if _strcspn(deletion, ' \n\r') == 0:
                deletion = deletion.replace('\r', '\\r').replace('\n', '\\n')
            return '<del>' + cgi.escape(deletion) + '</del>'
        else: # elif opcode == 'i':
            return '<ins>' + cgi.escape(from_[from_offset : from_offset + from_len]) + '</ins>'



if __name__ == '__main__':
    pass
