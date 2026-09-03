from state import State, RawRecord
from events import emit, GameOver, PlayerIdentity

def game_over_node(state: State) -> State:
    real_player_identity: PlayerIdentity = "spy" if state["real_player_id"] == state["spy_id"] else "civilian"
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

    return {
        "history": [RawRecord(content=f"词语揭晓：平民词：{state["word_civilian"]}，卧底词：{state["word_spy"]}", is_private=False, read_only_by=None)]
    }