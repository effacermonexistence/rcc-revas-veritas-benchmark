# Publication correction, revision 2

The archive in publication commit `4f6996329ec49c4968545e0c0235d463225d88b3` was truncated during the publisher upload. Its actual SHA-256 was `2ddccc871649b9a8d0f7630faace8918215d7c07b50a6ed9be119af6e661cf6a`, not the declared digest. Takeshi correctly stopped before extraction or execution.

This revision replaces the invalid archive. The recovered original source is unchanged: all 67 files produce Git tree `ab477cff7924b922b0885fb665e5ca0d6e42868a` from source commit `8692c48bc4f93b56ab019004c27b7c6fd9c8fe62`. No runtime rule, original fixture, label, or three-case semantic divergence was retuned.

The newly packaged archive digest is `4c736357ab93a8f4b5027b94c20340b973c760de1a0027df30bb53d3d10f47d8`. Do not substitute the corrupted archive digest or continue using the superseded publication pin. Publisher-side CI has checked archive integrity, source tree identity, all 160 tests, and the 13-stage reproduction. Partner independent verification and the native joint evaluation remain subsequent steps.
