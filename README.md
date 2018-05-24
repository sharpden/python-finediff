# python-finediff
This is Python port of https://github.com/gorhill/PHP-FineDiff, library for string diff.

```python
import finediff
finediff.FineDiff('abcdef', 'badefo').renderDiffToHTML()
```
`'<del>a</del>b<del>c</del><ins>a</ins>def<ins>o</ins>'`

### Installation

```bash
pip install https://github.com/sharpden/python-finediff/tarball/master
```
