from bs4 import BeautifulSoup
import datetime
import jinja2
import requests


def main():
    # ESPN considers ties to be losses, but we don't.
    # We don't have a way to infer ties from ESPN, so
    # are relying on this hardcoded list.
    #
    # Note that this list is 0-indexed,
    # so Week 1 is Item 0, Week 2 is item 1, etc
    #
    global ties
    ties = [ list() for week in range(1,18) ]
    #
    # For ex, if Cleveland tied Pittsburgh in Week 2:
    #    ties[1] = ["CLE", "PIT"]
    
    # This is a map of team_name -> array of week scores for that team
    # Each element in a team's array is that team's total score for that week
    teams_to_weekly_scores = {}

    # This is a map of team_name -> array of week records for that team
    # Each element in a team's array is that teams record (W-L-T) for that week
    teams_to_weekly_records = {}
    
    teams_to_weekly_scores, teams_to_weekly_records = build_weekly_maps()

    # Generates a map of team -> season-score for all teams
    unranked_team_totals = {}
    for team in teams_to_weekly_scores.keys():
        unranked_team_totals[team] = sum(teams_to_weekly_scores[team])

    ranked_team_totals = rank_team_totals(unranked_team_totals)

    # Render scoreboard
    render_scoreboard(ranked_team_totals,
                      teams_to_weekly_scores,
                      teams_to_weekly_records)


# Distinction between ranked and sorted is that
# ranked is aware of ties. We can have multiple
# second place teams, for example.
def rank_team_totals(unranked_team_totals):
    """Given a dict of unranked teams -> totals, generates a ranked list of tuples (rank, team, total)"""
    # Sort the teams -- highest season-score first
    sorted_team_totals = {k: v for k, v in sorted(unranked_team_totals.items(),
                                                  key=lambda item: item[1],
                                                  reverse=True)}
    
    # Generates list of tuples (Rank, Team, Score)
    ranked_team_totals = []
    rank = 1
    last_score = None
    for i,team in enumerate(sorted_team_totals):
        score = sorted_team_totals[team]
        if score != last_score:
            rank = i+1
        ranked_team_totals.append((rank, team, score))
        last_score = score
        
    return ranked_team_totals
    
def render_scoreboard(ranked_team_totals,
                      teams_to_weekly_scores,
                      teams_to_weekly_records):
    
    templateLoader = jinja2.FileSystemLoader(searchpath="./")
    templateEnv = jinja2.Environment(loader=templateLoader)
    TEMPLATE_FILE = "scoreboard.html"
    template = templateEnv.get_template(TEMPLATE_FILE)
    outputText = template.render(ranked_team_totals=ranked_team_totals,
                                 teams_to_weekly_scores=teams_to_weekly_scores,
                                 teams_to_weekly_records=teams_to_weekly_records,
                                 now=datetime.datetime.now())
    print(outputText)
    return
    
def build_weekly_maps():
    """Generates a map of team_name to an array of week scores for all teams in league"""
    
    teams_to_weekly_scores = {}
    teams_to_weekly_records = {}

    for week in range(1,18): # Should be 18
        week_index = week-1 # Just for readability..
        for group_pick_grid in get_group_pick_grids(week):
            for team_row in get_rows(group_pick_grid):
                team = get_name(team_row)
                if team not in teams_to_weekly_scores:
                    # First time we see them, initialize their arrays
                    teams_to_weekly_scores[team] = [None] * 17 # should be 17
                    teams_to_weekly_records[team] = [None] * 17 # should be 17
                teams_to_weekly_scores[team][week_index] = get_score_from_team_row(team_row, week=week)
                teams_to_weekly_records[team][week_index] = get_record_from_team_row(team_row, week=week)

    # Maybe used a NameTuple for "Scoreboard" or something like that..
    return (teams_to_weekly_scores, teams_to_weekly_records)

def get_rows(group_pick_grid):
    """Given a Group Pick Grid, returns a list of team rows"""
    return group_pick_grid.find_all("tr")

def get_name(team_row):
    """Given a Group Pick Grid Team Row, returns the team's name"""
    entry_td = team_row.find("td", class_="entryowner")
    team_name = entry_td.find("a", {"class": "entry"}).text
    owner = entry_td.find("a", {"class": "profileLink"}).text
    return f"{team_name} ({owner})"

def get_record_from_team_row(team_row, week=None):
    """Given a team row from ESPN 'Group Pick Grid', returns weekly record (W-L-T) for that team"""
    wins = 0
    losses = 0
    ties = 0
    
    for cell in team_row:
        # ESPN considers unpicked games losses
        # We ignore unpicked games
        if is_unpicked(cell):
            continue
        
        # We only care about wins/losses/ties
        # Ignoring all other cells and states
        if is_win(cell):
            wins += 1
        elif week is not None and is_tie(cell, week):
            ties += 1
        elif is_loss(cell):
            losses += 1
            
    return f"({wins}-{losses}-{ties})"

def get_score_from_team_row(team_row, week=None):
    """Given a team row from ESPN 'Group Pick Grid', returns weekly score for that team"""

    # Instead of a separate team_row parser, maybe derive this from (W-L-T) record string returned above
    
    score = 0
    for cell in team_row:
        # ESPN considers unpicked games losses
        # We ignore unpicked games
        if is_unpicked(cell):
            continue
        
        # We only care about wins/losses/ties
        # Ignoring all other cells and states
        if is_win(cell):
            score += 1
        elif is_tie(cell, week):
            continue
        elif is_loss(cell):
            score -= 2
    return score

#### Consider moving ESPN fetching and interpretation to espn_utils module

def is_unpicked(cell):
    """Given ESPN 'Group Pick Grid' cell, returns true if game was picked"""
    # This inverted logic is ugly, but makes the actual test cleaner above
    if cell.text == '--':
        return True
    else:
        return False


def is_win(cell):
    """Given ESPN 'Group Pick Grid' cell, returns true if game was picked correctly"""
    if "win" in cell['class']:
        return True
    else:
        return False

def is_loss(cell):
    """Given ESPN 'Group Pick Grid' cell, returns true if game was picked incorrectly"""

    if "loss" in cell['class']:
        return True
    else:
        return False

def is_tie(cell, week):
    """Given ESPN 'Group Pick Grid' cell, returns true if game was a tie""" 
    week_index = week - 1 # Just for readability
    
    # ESPN considers ties to be losses
    # We don't, but don't have a good way to infer a tie
    # So we check against a hardcoded tie list
    if "loss" in cell['class'] and cell.img is not None:
        team = cell.img['alt']
        if team in ties[week_index]:
            return True
    return False
    
def week_to_espn_links(week_num):
    """Given a week number (int), returns ESPN 'Group Pick Grid' url for that week"""
    urls = []
    base_url = "http://fantasy.espn.com/nfl-pigskin-pickem/2019/en/scoresheet?groupID=177507"

    # 120 is a magic number found by looking at ESPN XHR
    # Week 1 is period 120, Week 2 is 121, etc
    period=120+week_num-1
    urls.append(f"{base_url}&period={period}")
    urls.append(f"{base_url}&period={period}&objectStart=50")
    return urls

def get_group_pick_grids(week):
    """Given a week number, returns a list of ESPN 'Group Pick Grids' for that week"""

    table_bodies = []
    for url in week_to_espn_links(week):
        result = requests.get(url)
        soup = BeautifulSoup(result.content, "html.parser")

        # Magic class names based on manual inspection
        table_container = soup.find("div", {"class": "container scoresheet-container"})
        table = table_container.find("table", {"class": "type_entries"})
        table_bodies.append(table.find("tbody"))
        
    return table_bodies

if __name__ == '__main__':
    main()
