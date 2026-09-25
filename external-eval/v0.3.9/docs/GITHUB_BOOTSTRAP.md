# Repository publication

This delivered ZIP and Git bundle are local artifacts. They do not assert that a
remote repository or remote CI run exists. The old joint synthetic repository and
its pins are not modified.

After creating an authorized empty remote repository:

```bash
git clone rcc-revas-veritas-external-benchmark-reviewed.bundle external-eval
cd external-eval
# Use the actual approved remote URL, not a guessed repository.
git remote remove origin
git remote add origin APPROVED_REMOTE_URL
git push -u origin main
```

Review data/IP visibility before publishing. Shared technical source refs are in
SOURCE_REVIEW.md; private email bodies, credentials and original private mapping
attachments are not redistributed by this kit. Hash verification is mandatory
after transfer because the earlier RCC publication had an archive-identity defect.
