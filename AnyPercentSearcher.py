import requests
import time

PLATFORM_NAME = "GameCube"  # Set the platform name here
PLATFORM_EXCLUSIVE = False
RATE_LIMIT_ERROR_CODE = 420
RATE_LIMIT_TIMEOUT_SECONDS = 60
ANY_PERCENT_MIN_RUN_TIME = {"hours": 2, "minutes": 0}

# Function to get the platform's ID
def get_platform_id(platform_name):
    url = "https://www.speedrun.com/api/v1/platforms"
    next_page = True
    while next_page:
        response = requests.get(url)
        data = response.json()
        for platform in data['data']:
            if platform['name'] == platform_name:
                return platform['id']
        next_page_url = data['pagination']['links'][-1]['uri'] if data['pagination']['links'] else None
        if next_page_url and data['pagination']['links'][-1]['rel'] == 'next':
            url = next_page_url
        else:
            next_page = False
    return None

# Function to get games for the specified platform
def get_platform_games(platform_id):
    url = f"https://www.speedrun.com/api/v1/games?platform={platform_id}"
    next_page = True
    while next_page:
        response = requests.get(url)
        
        if response.status_code == RATE_LIMIT_ERROR_CODE:
            print(f"Rate limit reached when querying platform games. Waiting for {RATE_LIMIT_TIMEOUT_SECONDS} seconds before retrying.")
            time.sleep(RATE_LIMIT_TIMEOUT_SECONDS)
            continue
        
        data = response.json()
        
        if 'data' in data:
            for game in data['data']:
                if PLATFORM_EXCLUSIVE:
                    # Get the game's detailed information
                    game_url = f"https://www.speedrun.com/api/v1/games/{game['id']}"
                    game_response = requests.get(game_url)
                    game_data = game_response.json()

                    if 'data' in game_data and 'platforms' in game_data['data']:
                        platforms = game_data['data']['platforms']
                        # Check if the specified platform is the only platform
                        if len(platforms) == 1 and platforms[0] == platform_id:
                            yield game
                else:
                    yield game

        if 'pagination' in data and 'links' in data['pagination']:
            next_page_url = data['pagination']['links'][-1]['uri'] if data['pagination']['links'] else None
            if next_page_url and data['pagination']['links'][-1]['rel'] == 'next':
                url = next_page_url
            else:
                next_page = False
        else:
            print(data)
            next_page = False

# Function to get categories for a game
def get_category_data(game_id):
    categories_url = f"https://www.speedrun.com/api/v1/games/{game_id}/categories"
    categories_response = requests.get(categories_url)
    
    # Recurse on timeout
    if categories_response.status_code == RATE_LIMIT_ERROR_CODE:
        print(f"Rate limit reached when fetching category data. Waiting for {RATE_LIMIT_TIMEOUT_SECONDS} seconds before retrying.")
        time.sleep(RATE_LIMIT_TIMEOUT_SECONDS)
        return get_category_data(game_id)
    
    categories_data = categories_response.json()
    
    if 'data' in categories_data:
        return categories_data['data']
    return {}

# Function to get categories for a game
def get_leaderboard_data(game_id, categories_data):
    for category_data in categories_data:
        if category_data['name'] != 'Any%':
            continue
        
        leaderboard_url = f"https://www.speedrun.com/api/v1/leaderboards/{game_id}/category/{category_data['id']}"
        leaderboard_response = requests.get(leaderboard_url)
        
        # Recurse on timeout
        if leaderboard_response.status_code == RATE_LIMIT_ERROR_CODE:
            print(f"Rate limit reached when fetching leaderboard data. Waiting for {RATE_LIMIT_TIMEOUT_SECONDS} seconds before retrying.")
            time.sleep(RATE_LIMIT_TIMEOUT_SECONDS)
            return get_leaderboard_data(game_id, categories_data)
        
        leaderboard_data = leaderboard_response.json()
        
        if 'data' in leaderboard_data:
            return leaderboard_data['data']
    return {}

# Function to get the world record Any% time for a game
def get_world_record_any(game_id):
    categories_data = get_category_data(game_id)
    leaderboard_data = get_leaderboard_data(game_id, categories_data)
    
    if 'runs' in leaderboard_data:
        runs = leaderboard_data['runs']
        if len(runs) > 0:
            return runs[0]['run']['times']['primary_t']
                
    return None

platform_id = get_platform_id(PLATFORM_NAME)
print("Finding games for: " + platform_id)

if platform_id:
    platform_games = get_platform_games(platform_id)
    filter_min_run_time = ANY_PERCENT_MIN_RUN_TIME['hours'] * 3600 + ANY_PERCENT_MIN_RUN_TIME['minutes'] * 60

    for game in platform_games:
        world_record_time = get_world_record_any(game['id'])
        if world_record_time and world_record_time > filter_min_run_time:
            hours = int(world_record_time // 3600)
            minutes = int((world_record_time % 3600) // 60)
            print("{:3} hours {:2} minutes | {}".format(hours, minutes, game['names']['international']))
