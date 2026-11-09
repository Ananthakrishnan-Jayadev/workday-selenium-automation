# Page dumps

Raw HTML of real Workday pages, used to confirm and fix locators. This folder is git-ignored:
the dumps can contain your name, email and address.

## How to capture
1. Open the page in Chrome or Firefox and get it into the state described below.
2. Open DevTools (F12) → **Console**.
3. Run `copy(document.documentElement.outerHTML)`.
4. Open the matching file here, replace **everything** in it with the clipboard contents, and save.

**Prompt lists (e.g. "How did you hear") close as soon as focus leaves the page**, so a normal capture
misses them. Use a delayed capture instead:
1. In the Console run: `setTimeout(() => { window.__dump = document.documentElement.outerHTML; console.log('captured') }, 5000)`
2. Within 5 seconds, click into the page and open the list (type something, press Enter if needed), then wait.
3. After "captured" appears, run `copy(window.__dump)` and paste.

Most dropdowns (button style) stay open while you use DevTools. If one does close, press F8 in the
Sources tab to pause the page first, or use **Elements → right-click `<html>` → Copy → Copy outerHTML**.

## Files (CIBC)
| File | State to capture |
|---|---|
| `cibc_01_job_posting.html` | Posting page loaded, nothing clicked (the Apply button is visible) |
| `cibc_02_apply_popup.html` | After clicking **Apply**, while the popup with Autofill with Resume / Apply Manually / Use My Last Application is open |
| `cibc_03_create_account.html` | After clicking **Apply Manually**, signed out: the Create Account form |
| `cibc_04_sign_in.html` | After clicking the **Sign In** link on that form, before typing anything |
| `cibc_05_my_information.html` | Signed in, first page of the application, before filling anything |

**Optional extras** for `cibc_05`, which help with the dropdowns:
- `cibc_05b_my_information_dropdown_open.html`: same page with the **Country** or **Province** dropdown open.
- `cibc_05c_my_information_source_open.html`: same page with the **How did you hear about us** list open.
- `cibc_05d_my_information_errors.html`: click **Save and Continue** with the form empty, then capture
  the page showing the validation errors.

Later phases will add `cibc_06_my_experience.html` and so on. From Phase 1 on,
`python tools/dump_page.py` saves these automatically while a run is paused.
