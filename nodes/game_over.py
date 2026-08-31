from state import State, PlayerIdentity
from events import emit, GameOver

def game_over_node(state: State):
    real_player_identity = PlayerIdentity.SPY if state["real_player_id"] == state["spy_id"] else PlayerIdentity.CIVILIAN
    is_real_player_win = real_player_identity == state["winner"]

    emit(GameOver(
        winner=state["winner"], 
        real_player_identity=real_player_identity,
        is_real_player_win=is_real_player_win,
        real_player_id=state["real_player_id"],
        spy_id=state["spy_id"],
        word_civilian=state["word_civilian"], 
        word_spy=state["word_spy"],
    ))