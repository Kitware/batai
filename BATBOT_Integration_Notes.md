# BatBot Integration Notes

BatBot has some git lfs issues with installing initially
requires the `UV_GIT_LFS=1` to be set
As well as `GIT_LFS_SKIP_SMUDGE=1`

Batbot data exported:
Files of the structure: '01of01.compressed.jpg'
Also for uncompressed is '01of02.jpg' and '02of02.jpg'

There us a metadata.json file that is exported out from the code

Document the structure of this metadata json data
It needs to be converted into the widths, starts, stops, and length
`size.uncompressed.width.px`
`size.compressed.width.px`
`segments` is an array that can be formatted by extracting
`segments[0]["start.ms"]`
`segments[0]["end.ms"]`

From there we have the total width and the total time for the invidiual segments we can calulate a pixels/ms

Might need to see if we can change it so that the sytstem instead uses a way where we use the raw time and
don't use the invividual widths at all for calculations.  This may require some front end work as well.

Tasks:

- ~~Add batbot dependency to UV installation~~
- ~~Swap spectrogram creation to use batbot pipeline without a config~~
- ~~Create a converter to calculate the length, starts, stops, widths~~

Updates:

- batbot is added a dependency
- tasks.py is updated so that the utilities the new batbot function to create spectrograms
- inference is disabled

TODO:

- Remove older generation code from the system
- remove inference code from the system
- Remove the local installation of batbot once updated from:
  - docker-compose.overrride.yml
  - pyproject.toml
  - uv.lock
- Can temporarily use my branch on the repo (issue-4-output-folder-option)
- Update sample script uv dependencies when batbot is published
