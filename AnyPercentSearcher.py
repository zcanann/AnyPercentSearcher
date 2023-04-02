import requests
import time

# To pipe results to a file, run:
# python -u AnyPercentSearcher.py > Results.txt
# This script may take a few hours for platforms with a lot of games, such as PC

# Configuration
PLATFORM_NAME = "GameCube"
ANY_PERCENT_MIN_RUN_TIME = {"hours": 2, "minutes": 0}
PLATFORM_EXCLUSIVE = False # Enable to filter out games that are republished on multiple platforms (ie PC + GameCube)
GENRES_TO_INCLUDE = [] # Leave as [] to skip including specific genre(s). Example: ["Action", "Adventure"]
GENRES_TO_EXCLUDE = [] # Leave as [] to skip excluding specific genre(s). Example: ["Racing"]
PRINT_RETRY_INFO = True

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

    # If a valid platform ID is found, get platform games and filter based on the minimum run time
    if platform_id:
        platform_games = get_platform_games(platform_id, genre_ids_to_include, genre_ids_to_exclude)
        filter_min_run_time = ANY_PERCENT_MIN_RUN_TIME['hours'] * 3600 + ANY_PERCENT_MIN_RUN_TIME['minutes'] * 60

        # Iterate through the games and print the ones that meet the time filter criteria
        for game in platform_games:
            world_record_time = get_world_record_any(game['id'])
            if world_record_time and world_record_time > filter_min_run_time:
                hours = int(world_record_time // 3600)
                minutes = int((world_record_time % 3600) // 60)
                print("{:3} hours {:2} minutes | {}".format(hours, minutes, game['names']['international']))

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

def get_platform_games(platform_id, genre_ids_to_include, genre_ids_to_exclude):
    """
    Get a list of games for the specified platform, filtered by genre.

    Args:
        platform_id (str): The ID of the platform to search for games.
        genre_ids_to_include (list): A list of genre IDs to include.
        genre_ids_to_exclude (list): A list of genre IDs to exclude.

    Yields:
        dict: A game that matches the platform and genre filters.
    """
    
    def _get_game_detailed_data(game_id):
        game_url = f"https://www.speedrun.com/api/v1/games/{game_id}"
        game_response = requests.get(game_url)
        game_data = game_response.json()
        return game_data

    url = f"https://www.speedrun.com/api/v1/games?platform={platform_id}"
    next_page = True

    while next_page:
        response = requests.get(url)

        if response.status_code == RATE_LIMIT_ERROR_CODE:
            if PRINT_RETRY_INFO:
                print(f"Rate limit reached when querying platform games. Waiting for {RATE_LIMIT_TIMEOUT_SECONDS} seconds before retrying.")
            time.sleep(RATE_LIMIT_TIMEOUT_SECONDS)
            continue

        data = response.json()

        # Process games in the current page
        if 'data' in data:
            for game in data['data']:
                if not 'genres' in game:
                    continue
                if len(genre_ids_to_include) > 0 and not set(genre_ids_to_include).intersection(game['genres']):
                    continue
                if len(genre_ids_to_exclude) > 0 and set(genre_ids_to_exclude).intersection(game['genres']):
                    continue
                if PLATFORM_EXCLUSIVE:
                    game_data = _get_game_detailed_data(game['id'])
                    if 'data' in game_data and 'platforms' in game_data['data']:
                        platforms = game_data['data']['platforms']
                        if len(platforms) == 1 and platforms[0] == platform_id:
                            yield game
                else:
                    yield game

        # Check for the next page
        if 'pagination' in data and 'links' in data['pagination']:
            next_page_url = data['pagination']['links'][-1]['uri'] if data['pagination']['links'] else None
            if next_page_url and data['pagination']['links'][-1]['rel'] == 'next':
                url = next_page_url
            else:
                next_page = False
        else:
            print(data)
            next_page = False

def get_category_data(game_id):
    """
    Retrieve categories data for the specified game from the Speedrun.com API.
    
    Args:
        game_id (str): The ID of the game to fetch categories for.

    Returns:
        list: A list of dictionaries containing category data, or an empty list if data not found or rate limit is reached.
    """
    categories_url = f"https://www.speedrun.com/api/v1/games/{game_id}/categories"
    categories_response = requests.get(categories_url)
    
    # Handle rate limit and wait before retrying
    if categories_response.status_code == RATE_LIMIT_ERROR_CODE:
        if PRINT_RETRY_INFO:
            print(f"Rate limit reached when fetching category data. Waiting for {RATE_LIMIT_TIMEOUT_SECONDS} seconds before retrying.")
        time.sleep(RATE_LIMIT_TIMEOUT_SECONDS)
        return get_category_data(game_id)
    
    categories_data = categories_response.json()
    
    # Return the 'data' field if it exists, otherwise return an empty list
    return categories_data.get('data', [])

def get_leaderboard_data(game_id, categories_data):
    """
    Retrieve leaderboard data for the specified game and categories from the Speedrun.com API.

    Args:
        game_id (str): The ID of the game to fetch leaderboard data for.
        categories_data (list): A list of dictionaries containing category data.

    Returns:
        dict: A dictionary containing leaderboard data for the Any% category, or an empty dictionary if data not found or rate limit is reached.
    """
    for category_data in categories_data:
        if category_data['name'] != 'Any%':
            continue

        leaderboard_url = f"https://www.speedrun.com/api/v1/leaderboards/{game_id}/category/{category_data['id']}"
        leaderboard_response = requests.get(leaderboard_url)

        # Handle rate limit and wait before retrying
        if leaderboard_response.status_code == RATE_LIMIT_ERROR_CODE:
            if PRINT_RETRY_INFO:
                print(f"Rate limit reached when fetching leaderboard data. Waiting for {RATE_LIMIT_TIMEOUT_SECONDS} seconds before retrying.")
            time.sleep(RATE_LIMIT_TIMEOUT_SECONDS)
            return get_leaderboard_data(game_id, categories_data)

        leaderboard_data = leaderboard_response.json()

        # Return the 'data' field if it exists, otherwise return an empty dictionary
        return leaderboard_data.get('data', {})
    return {}

def get_world_record_any(game_id):
    """
    Retrieve the world record Any% time for the specified game from the Speedrun.com API.

    Args:
        game_id (str): The ID of the game to fetch the world record Any% time for.

    Returns:
        float: The world record Any% time in seconds, or None if data not found or rate limit is reached.
    """
    categories_data = get_category_data(game_id)
    leaderboard_data = get_leaderboard_data(game_id, categories_data)

    if 'runs' in leaderboard_data:
        runs = leaderboard_data['runs']
        if len(runs) > 0:
            return runs[0]['run']['times']['primary_t']

    return None

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
