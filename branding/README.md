# Chat Chacha branding

This branch (`chatchacha-brand`) holds only what makes Warmbly look like Chat Chacha.
Upstream code is never edited here: `.github/workflows/chatchacha-images.yml` checks
out an untouched Warmbly release, runs `apply.py`, and publishes the images the
server at email.chatchacha.in pulls (`WARMBLY_IMAGE_PREFIX=ghcr.io/chatchacha-in/warmbly`).

- `brand.json` – name, assistant name, colours (Tailwind sky scale repainted purple).
- `assets/logo.png` – the logo; favicons and app icons are generated from it.
- `apply.py` – the transformation. It fails loudly if upstream moved something it patches.

Runs daily at 08:00 IST and builds any new Warmbly release; run it by hand from the
Actions tab ("Chat Chacha images" → Run workflow) to rebuild a tag.

Runtime branding that needs no rebuild lives in the server's `.env`:
`EMAIL_BRAND_NAME`, `EMAIL_BRAND_WEBSITE_URL`, `EMAIL_BRAND_SUPPORT_EMAIL`
(and `EMAIL_BRAND_TERMS_URL` / `EMAIL_BRAND_PRIVACY_URL` once those pages exist).
