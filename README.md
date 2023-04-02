# AnyPercentSearcher
Script to search speedrun.com for Any% games, filtering by platform and world record time. 

This is helpful for finding games to Glitch Hunt. I've been meaning to write this script for years, but never wanted to learn the speedrun API.

Fortunately, thanks to ChatGPT 4, was able to finally write this script in under 2 hours. Probably would have taken me days otherwise.

### Setup
Be sure to `pip install requests` before running the script.

### Running the Script
Just modify the global variables at the top as needed, or the script itself if something custom is required. This script may take a few hours for platforms with a lot of games, such as PC

Once you verify that the script works, you may want to set `PRINT_RETRY_INFO = False` to avoid output clutter.

To pipe results to a file, run:
`python -u AnyPercentSearcher.py > Results.txt`
