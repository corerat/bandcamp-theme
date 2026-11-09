# bandcamp look

this folder has the colors, background, and custom header i made for my bandcamp page. the images and scripts stay together so i can change them and make them again later.

## files

- `bandcamp-color-palette.txt` has the colors to enter in bandcamp's design settings.
- `bandcamp-background.png` is the repeating purple texture.
- `bandcamp-header.png` is the 975 by 180 custom header. its bottom edge blends into the `#382448` navigation bar.
- `generate_bandcamp_background.py` makes the repeating background.
- `generate_bandcamp_header.py` makes the custom header.

## making the images again

python 3 and its standard library are all these scripts need. from this folder, run:

```sh
python3 generate_bandcamp_background.py
python3 generate_bandcamp_header.py
```

both scripts use a fixed seed, so running them again makes the same images. use `--seed` to make a different version, or `--output` to choose where to save it:

```sh
python3 generate_bandcamp_background.py --seed 1234
python3 generate_bandcamp_header.py --seed 1234
```

the image colors and texture settings are near the top of each script. the header size is set to bandcamp's 975 by 180 limit.
