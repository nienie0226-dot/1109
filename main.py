
import os
import random
import uuid
from typing import Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Wordle API Server")

# CORS 設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 五字母英文單字字典
WORD_BANK = {
    "APPLE", "TRAIN", "HOUSE", "PLANT", "SMART",
    "WORLD", "LIGHT", "BRAIN", "CLOUD", "WATER",
    "ABOUT", "ABOVE", "ACTOR", "ACUTE", "ADMIT",
    "ADOPT", "ADULT", "AFTER", "AGAIN", "AGENT",
    "AGREE", "AHEAD", "ALARM", "ALBUM", "ALERT",
    "ALIEN", "ALIKE", "ALIVE", "ALLOW", "ALONE",
    "ALONG", "ALTER", "AMONG", "ANGER", "ANGLE",
    "ANGRY", "APART", "APPLY", "ARGUE", "ARISE",
    "ARRAY", "ARROW", "ASIDE", "ASSET", "AUDIO",
    "AUDIT", "AVOID", "AWAKE", "AWARE", "BADGE",
    "BAKER", "BASIC", "BASIS", "BEACH", "BEGIN",
    "BEING", "BELOW", "BENCH", "BLACK", "BLAME",
    "BLANK", "BLAST", "BLEED", "BLEND", "BLOCK",
    "BLOOD", "BOARD", "BOAST", "BONUS", "BOOST",
    "BOUND", "BREAD", "BREAK", "BRICK", "BRIEF",
    "BRING", "BROAD", "BROWN", "BRUSH", "BUILD",
    "BUNCH", "BUYER", "CABLE", "CANDY", "CARGO",
    "CARRY", "CATCH", "CAUSE", "CHAIN", "CHAIR",
    "CHALK", "CHARM", "CHART", "CHASE", "CHEAP",
    "CHECK", "CHEST", "CHIEF", "CHILD", "CHOSE",
    "CIVIL", "CLAIM", "CLASS", "CLEAN", "CLEAR",
    "CLIMB", "CLOCK", "CLOSE", "COACH", "COAST",
    "COUNT", "COURT", "COVER", "CRASH", "CREAM",
    "CRIME", "CROSS", "CROWD", "CROWN", "CURVE",
    "CYCLE", "DAILY", "DANCE", "DEATH", "DELAY",
    "DEPTH", "DRAFT", "DRAMA", "DREAM", "DRIVE",
    "EAGLE", "EARLY", "EARTH", "EIGHT", "EMPTY",
    "ENEMY", "ENJOY", "ENTER", "EQUAL", "ERROR",
    "EVENT", "EVERY", "EXACT", "EXIST", "FAITH",
    "FALSE", "FAULT", "FIELD", "FIGHT", "FINAL",
    "FIRST", "FLAME", "FLASH", "FLOAT", "FLOOR",
    "FLOUR", "FLUID", "FOCUS", "FORCE", "FORTH",
    "FORTY", "FORUM", "FRAME", "FRESH", "FRONT",
    "FRUIT", "GIANT", "GLASS", "GLOBE", "GRACE",
    "GRADE", "GRAND", "GRANT", "GRASS", "GREAT",
    "GREEN", "GROUP", "GUARD", "GUESS", "GUIDE",
    "HAPPY", "HEART", "HEAVY", "HOTEL", "HUMAN",
    "IMAGE", "INDEX", "INPUT", "ISSUE", "JUDGE",
    "KNIFE", "LAYER", "LEMON", "LEVEL", "LIMIT",
    "LUNCH", "MAGIC", "MAJOR", "MARCH", "MATCH",
    "MEDAL", "MONEY", "MONTH", "MUSIC", "NIGHT",
    "NOVEL", "NURSE", "OCEAN", "OFFER", "ORDER"
}

MAX_ATTEMPTS = 6

# 遊戲資料
games_db: Dict[str, dict] = {}


class GuessRequest(BaseModel):
    game_id: str
    guess: str
    hard_mode: bool = False


# 首頁測試
@app.get("/")
def home():
    return {
        "message": "Wordle API Server is running."
    }


# 查詢累計統計
@app.get("/api/stats")
def get_stats():

    wins = sum(
        1 for game in games_db.values()
        if game["status"] == "WON"
    )

    losses = sum(
        1 for game in games_db.values()
        if game["status"] == "LOST"
    )

    played = wins + losses

    win_rate = round(
        wins / played * 100, 1
    ) if played else 0.0

    return {
        "games_played": played,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate
    }


# 建立新遊戲
@app.post("/api/new-game")
def start_new_game():

    game_id = str(uuid.uuid4())

    target_word = random.choice(sorted(WORD_BANK))

    games_db[game_id] = {
        "target": target_word,
        "status": "PLAYING",
        "attempts": 0,
        "history": []
    }

    return {
        "game_id": game_id,
        "message": "New game started!",
        "max_attempts": MAX_ATTEMPTS
    }


# 判斷字母顏色
def make_feedback(guess, target):

    feedback = ["absent"] * 5

    remaining_letters = {}

    # 第一輪：先判斷綠色
    for i in range(5):

        if guess[i] == target[i]:

            feedback[i] = "correct"

        else:

            letter = target[i]

            remaining_letters[letter] = (
                remaining_letters.get(letter, 0) + 1
            )

    # 第二輪：判斷黃色
    for i in range(5):

        if feedback[i] == "correct":
            continue

        letter = guess[i]

        if remaining_letters.get(letter, 0) > 0:

            feedback[i] = "present"

            remaining_letters[letter] -= 1

    return feedback


# Hard Mode 規則檢查
def check_hard_mode(guess, history):

    required_positions = {}

    required_counts = {}

    for item in history:

        old_guess = item["guess"]

        old_feedback = item["feedback"]

        for i, result in enumerate(old_feedback):

            letter = old_guess[i]

            # 綠色字母必須固定位置
            if result == "correct":

                required_positions[i] = letter

            # 綠色及黃色字母必須保留
            if result in ("correct", "present"):

                required_counts[letter] = (
                    required_counts.get(letter, 0) + 1
                )

    # 檢查綠色位置
    for position, letter in required_positions.items():

        if guess[position] != letter:

            return (
                f"Hard Mode: Position {position + 1} "
                f"must be {letter}."
            )

    # 檢查必要字母數量
    for letter, count in required_counts.items():

        if guess.count(letter) < count:

            return (
                f"Hard Mode: Your guess must contain "
                f"at least {count} '{letter}' letter(s)."
            )

    return None


# 接收玩家猜測
@app.post("/api/guess")
def process_guess(req: GuessRequest):

    game_id = req.game_id

    guess = req.guess.strip().upper()

    # 檢查遊戲是否存在
    if game_id not in games_db:

        raise HTTPException(
            status_code=404,
            detail="Game session not found."
        )

    game = games_db[game_id]

    # 檢查遊戲是否結束
    if game["status"] != "PLAYING":

        raise HTTPException(
            status_code=400,
            detail="This game has already ended."
        )

    # 檢查輸入格式
    if (
        len(guess) != 5
        or not guess.isascii()
        or not guess.isalpha()
    ):

        raise HTTPException(
            status_code=400,
            detail="Please enter exactly 5 English letters."
        )

    # 字典驗證
    if guess not in WORD_BANK:

        raise HTTPException(
            status_code=400,
            detail="Word is not in the dictionary."
        )

    # Hard Mode 驗證
    # 必須在增加猜測次數之前檢查
    if req.hard_mode:

        error = check_hard_mode(
            guess,
            game["history"]
        )

        if error:

            raise HTTPException(
                status_code=400,
                detail=error
            )

    target = game["target"]

    feedback = make_feedback(
        guess,
        target
    )

    # 有效猜測才增加次數
    game["attempts"] += 1

    game["history"].append({
        "guess": guess,
        "feedback": feedback
    })

    is_correct = guess == target

    # 判斷遊戲結果
    if is_correct:

        game["status"] = "WON"

    elif game["attempts"] >= MAX_ATTEMPTS:

        game["status"] = "LOST"

    game_ended = game["status"] != "PLAYING"

    return {
        "guess": guess,
        "feedback": feedback,
        "is_correct": is_correct,
        "status": game["status"],
        "attempts_used": game["attempts"],
        "attempts_remaining": (
            MAX_ATTEMPTS - game["attempts"]
        ),
        "history": game["history"],

        # 第六次猜錯或猜對才回傳答案
        "target_word": target if game_ended else None
    }


# 啟動伺服器
if __name__ == "__main__":

    import uvicorn

    port = int(os.environ.get("PORT", "8000"))

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port
    )
