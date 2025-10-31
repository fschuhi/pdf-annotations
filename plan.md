## test pdf unchanged
### seeds:
- `(Albini 2013) On dealing with destructive emotions.pdf` (unchanged)
- `(Albini 2013).md` as in `tests/tmp/complete_update_workflow/(Albini 2013).md`(annotations match the pdf)

### golden: n/a, we check that mtime of `(Albini 2013).md` wasn't touched


## test new pdf
### seeds:
- `(Albini 2013) On dealing with destructive emotions.pdf` (unchanged)
- `(Balbini 2014) On dealing with constructive emotions.pdf` (pdf has no annotations)
- no `(Albini 2013).md`
- no `(Balbini 2014).md`

### golden
- like `tests/fixtures/complete_update_workflow/goldens/(Albini 2013).md`
- `(Balbini 2014).md` has frontmatter, `pdf-annot-sep` and ends on `pdf-annot-info`(+ empty line)

## test one unchanged (with manual note text), one changed (with manual note text)
### seeds:
- `(Albini 2013) On dealing with destructive emotions.pdf` (unchanged)
- `(Calbini 2015) On disregarding destructive emotions.pdf` (unchanged `(Albini 2013)`)
- `(Albini 2013).md` as in `tests/tmp/complete_update_workflow/(Albini 2013).md` (annotations match the pdf, BUT: `.md` slightly changed with manually added text between frontmatter and annotations)
- `(Calbini 2015).md` as in `tests/fixtures/complete_update_workflow/seeds/(Albini 2013).md` (faked old annotations, BUT: `.md` has manually added text)

### golden
- check that mtime of `(Albini 2013).md` wasn't touched
- `(Calbini 2014).md` as in `tests/fixtures/complete_update_workflow/goldens/(Albini 2013).md` (but with manually added text)


## other tests (not yet fleshed out):
- (parts of) frontmatter missing in a note -> trigger note refresh
- test note exists but doesn't have frontmatter or annotations

## potential pdfs:
(Albini 2013) On dealing with destructive emotions.pdf
(Balbini 2014) On dealing with constructive emotions.pdf
(Calbini 2015) On disregarding destructive emotions.pdf
(Dalbini 2016) On disregarding constructive emotions.pdf
