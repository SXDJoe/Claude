# GP peer document: PDF build kit

Builds the two PDFs of the Governance Paradox peer document from the same page as the artifact. Every build uses the same page, the same fonts and the same page size, so the output stays consistent with the artifact design.

Output, one 16:9 frame per page (13.33 x 7.5 in, 12 pages):

- `GP_Peer_Document_print.pdf`: light palette, for printing.
- `GP_Peer_Document_screen.pdf`: dark palette, as on screen.

## Files

| File | What it is |
|---|---|
| `build_pdfs.py` | The build script. Python 3.8+, standard library only. |
| `pdf-content.json` | The text in the PDFs. Edit this file to change the PDF text. |
| `page.html` | The artifact page (layout, colours, fonts). OneDrive copy only; in the repo the script uses `../index.html`. |
| `fonts/` | Created on the first run. The script downloads the page's Google Fonts once and reuses them. |

## Run it

Needs Python 3 and Chrome or Edge installed.

```
python build_pdfs.py
```

The PDFs are written to the folder above this kit (`OUTPUTS/gp-marketing-deck`), replacing the previous versions.

Options: `--out <folder>` for another output folder, `--chrome <path to chrome.exe or msedge.exe>` if the browser is not found, `--content <file>` for another text file.

## Check the result

The script prints one line per PDF. `OK` means:

- the design fonts (Libre Caslon) are embedded; a PDF with fallback fonts is flagged;
- 12 pages at 960 x 540 pt;
- the phone number and the last line of the problem statement are in the text.

The page and text checks need `pypdf` (`pip install pypdf`). Without it the script still checks the fonts and says the rest was not checked.

Anything other than `OK`: do not send the PDFs.

## Which text is the source

- The live artifact holds the locked page text (`content.json` in the artifact).
- `pdf-content.json` is the artifact text plus two edits Joe chose from the md on 27 September 2026: the Team paragraph and the Stage 2 escalation paragraph.
- `GP_Peer_Document.md` (Block 2) matches `pdf-content.json`.

When the text changes, change `pdf-content.json` and the md together, then rebuild.

## Page layout changes

The script keeps the page's phone layout off the PDF. If the page's CSS is restructured, the script stops with "Page layout changed" instead of printing a broken layout. Update `build_pdfs.py` before building.

Source of truth for the kit: repo `SXDJoe/Claude`, folder `gp-peer-page/build/`. The OneDrive copy in `OUTPUTS/gp-marketing-deck/pdf-build/` is a working copy of it.
