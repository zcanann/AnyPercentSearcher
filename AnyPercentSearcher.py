import requests
import time
import srcomapi, srcomapi.datatypes as dt

api = srcomapi.SpeedrunCom()

# Configuration
PLATFORM_NAME = "PC"
ANY_PERCENT_MIN_RUN_TIME = {"hours": 1, "minutes": 0}
PLATFORM_EXCLUSIVE = False # Enable to filter out games that are republished on multiple platforms (ie PC + GameCube)
GENRES_TO_INCLUDE = [] # Leave as [] to skip including specific genre(s). Example: ["Action", "Adventure"]
GENRES_TO_EXCLUDE = [] # Leave as [] to skip excluding specific genre(s). Example: ["Racing"]
PRINT_RETRY_INFO = False

# Advanced Configuration
RATE_LIMIT_TIMEOUT_SECONDS = 60

# Globals
RATE_LIMIT_ERROR_CODE = 420

def main():
    # Get the platform ID for the specified platform name
    print(f"Finding platform id for {PLATFORM_NAME}...")
    platform_id = get_platform_id(PLATFORM_NAME)
    print(f"Found platform id: {platform_id}")

    # Get the genre IDs to include and exclude based on the global lists
    if len(GENRES_TO_INCLUDE) > 0 or len(GENRES_TO_EXCLUDE) > 0:
        print(f"Finding genre ids for {GENRES_TO_INCLUDE} / {GENRES_TO_EXCLUDE}...")
        genre_ids_to_include, genre_ids_to_exclude = get_genre_ids_to_include_and_exclude()
        print(f"Found genre ids: {genre_ids_to_include} / {genre_ids_to_exclude}")
    else:
        genre_ids_to_include = []
        genre_ids_to_exclude = []
    
    games = get_games(platform_id)
    filter_min_run_time = ANY_PERCENT_MIN_RUN_TIME['hours'] * 3600 + ANY_PERCENT_MIN_RUN_TIME['minutes'] * 60
    
    for game in games:
        categories = game.categories
        if len(categories) <= 0:
            continue
        records = categories[0].records
        if len(records) <= 0:
            continue
        runs = records[0].runs
        if len(runs) <= 0:
            continue
        world_record_time = runs[0]["run"].times['primary_t']
        if world_record_time and world_record_time >= filter_min_run_time:
            hours = int(world_record_time // 3600)
            minutes = int((world_record_time % 3600) // 60)
            print("{:3} hours {:2} minutes | {}".format(hours, minutes, game.name))
        
def get_platform_id(platform_name):
    """
    Get the platform's ID from the Speedrun.com API.

    Args:
        platform_name (str): The name of the platform to search for.

    Returns:
        str: The ID of the platform, or None if not found.
    """
    url = "https://www.speedrun.com/api/v1/platforms"
    while True:
        response = requests.get(url)
        data = response.json()

        # Iterate through platforms in the current page to find a match
        for platform in data['data']:
            if platform['name'] == platform_name:
                return platform['id']

        # Check for the next page, if any
        next_page_url = None
        for link in data['pagination']['links']:
            if link['rel'] == 'next':
                next_page_url = link['uri']
                break

        # If there is a next page, update the URL, otherwise exit the loop
        if next_page_url:
            url = next_page_url
        else:
            break

    return None

def get_games(platform_id):
    """
    Retrieve the world record Any% time for the specified game from the Speedrun.com API.

    Args:
        platform_id (str): The ID of the platform for which games are fetched.

    Returns:
        Game: The srcom object containing game data
    """
    
    # Number of games to fetch per request
    max_results = 200
    offset = 0

    while True:
        games = api.search(dt.Game, {"platform": platform_id, "max": max_results, "offset": offset})
        
        # Exit if no more games left
        if not games:
            break

        for game in games:
            yield game
        
        offset += max_results
            
def get_world_record_any(game_id):
    """
    Retrieve the world record Any% time for the specified game from the Speedrun.com API.

    Args:
        game_id (str): The ID of the game to fetch the world record Any% time for.

    Returns:
        float: The world record Any% time in seconds, or None if data not found or rate limit is reached.
    """
    while True:
        games = api.search(dt.Game, {"platform": platform_id, "max": max_results, "offset": offset})
        
        # Exit if no more games left
        if not games:
            break

        for game in games:
            categories = game.categories
            if len(categories) <= 0:
                continue
            records = categories[0].records
            if len(records) <= 0:
                continue
            runs = records[0].runs
            if len(runs) <= 0:
                continue
            world_record_time = runs[0]["run"].times['primary_t']

def get_genre_ids_to_include_and_exclude():
    """
    Retrieve a list of genre IDs to include and exclude based on the global GENRES_TO_INCLUDE and GENRES_TO_EXCLUDE lists.

    Returns:
        tuple: A tuple containing two lists: genre_ids_to_include and genre_ids_to_exclude.
    """
    url = "https://www.speedrun.com/api/v1/genres"
    genre_ids_to_include = []
    genre_ids_to_exclude = []

    while True:
        response = requests.get(url)

        # Handle rate limit and wait before retrying
        if response.status_code == RATE_LIMIT_ERROR_CODE:
            if PRINT_RETRY_INFO:
                print(f"Rate limit reached when querying genre IDs. Waiting for {RATE_LIMIT_TIMEOUT_SECONDS} seconds before retrying.")
            time.sleep(RATE_LIMIT_TIMEOUT_SECONDS)
            continue

        data = response.json()

        # Iterate through genres in the current page and add matching genre IDs to the lists
        for genre in data['data']:
            if genre['name'] in GENRES_TO_INCLUDE:
                genre_ids_to_include.append(genre['id'])
            elif genre['name'] in GENRES_TO_EXCLUDE:
                genre_ids_to_exclude.append(genre['id'])

        # Check for the next page
        if 'pagination' in data and 'links' in data['pagination']:
            next_page_url = data['pagination']['links'][-1]['uri'] if data['pagination']['links'] else None
            if next_page_url and data['pagination']['links'][-1]['rel'] == 'next':
                url = next_page_url
            else:
                break
        else:
            print(data)
            break

    return genre_ids_to_include, genre_ids_to_exclude

if __name__ == '__main__':
    main()
