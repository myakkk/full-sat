import json
from datetime import datetime
from supabase import create_client, Client
import random
import os
import certifi 

# --- SSL ҚАТЕСІН ТҮЗЕТУ ---
os.environ['SSL_CERT_FILE'] = certifi.where()

# --- БАПТАУЛАР ---
SUPABASE_URL = "https://kgdhjkuaufsinbyaltin.supabase.co"
SUPABASE_KEY = "sb_publishable_ocFzfPWfI6pGgFJvV8Fchw_13v5T7sM"

# Клиентті іске қосу
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"Supabase қосылу қатесі: {e}")

# Сұрақтарды импорттау
try:
    from questions import ALL_DATA, READING_DATA
except ImportError:
    ALL_DATA = {}
    READING_DATA = []

def init_db():
    """Базаны тексереді және сұрақтар жоқ болса, жүктейді."""
    try:
        response = supabase.table('questions').select("id", count="exact").execute()
        count = response.count
        
        # Егер база бос болса (немесе сіз тазаласаңыз)
        if count == 0:
            print("База бос, сұрақтар жүктелуде...")
            bulk_data = []

            # --- ТҮЗЕТІЛГЕН ЖЕРІ ОСЫНДА ---
            mapping = {
                "history": "Қазақстан тарихы",
                "math": "Математикалық сауаттылық", # Бұл questions.py ішіндегі "math" тізіміне сәйкес
                "math1": "Математика",             # Бұл questions.py ішіндегі "math1" тізіміне сәйкес (ТҮЗЕТІЛДІ)
                "informatics": "Информатика"
            }
            # -------------------------------

            for key, qs in ALL_DATA.items():
                if key == "reading": continue
                
                # Егер кілт mapping-те жоқ болса, оны өткізіп жібереміз немесе сол күйінде аламыз
                subject_name = mapping.get(key)
                if not subject_name: continue 

                for q in qs:
                    bulk_data.append({
                        "subject": subject_name,
                        "question": q['q'],
                        "options": json.dumps(q['opts']),
                        "answer": q['a'],
                        "explanation": q.get('explanation', ''),
                        "context": None
                    })

            # 2. Оқу сауаттылығы (Мәтіндік сұрақтар)
            for item in READING_DATA:
                text_passage = item["text"]
                for q in item["questions"]:
                    bulk_data.append({
                        "subject": "Оқу сауаттылығы",
                        "question": q['q'],
                        "options": json.dumps(q['opts']),
                        "answer": q['a'],
                        "explanation": "",
                        "context": text_passage
                    })
            
            # Базаға салу (100-ден бөліп, қате шықпас үшін)
            chunk_size = 100
            for i in range(0, len(bulk_data), chunk_size):
                supabase.table('questions').insert(bulk_data[i:i+chunk_size]).execute()
            print("Сұрақтар сәтті жүктелді!")
        else:
            print("Базада сұрақтар бар, жүктеу қажет емес.")
            
    except Exception as e:
        print(f"init_db қатесі: {e}")

# --- ҚОЛДАНУШЫЛАР ---
def login_user(username, password):
    try:
        response = supabase.table('users').select("*").eq('username', username).eq('password', password).execute()
        if response.data:
            return response.data[0]
    except: pass
    return None

def register_user(username, full_name, password):
    try:
        check = supabase.table('users').select("id").eq('username', username).execute()
        if check.data:
            return False
        
        supabase.table('users').insert({
            "username": username,
            "full_name": full_name,
            "password": password,
            "role": "student" 
        }).execute()
        return True
    except: return False

def change_password(user_id, new_password):
    try:
        supabase.table('users').update({"password": new_password}).eq('id', user_id).execute()
        return True
    except Exception as e:
        print(f"Password change error: {e}")
        return False

# --- ТЕСТ ЖӘНЕ НӘТИЖЕЛЕР ---
def save_result(user_id, subject, score, total):
    try:
        supabase.table('results').insert({
            "user_id": user_id,
            "subject": subject,
            "score": score,
            "total": total,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "is_active": True 
        }).execute()
    except Exception as e: print(f"Қате: {e}")

def get_questions_by_subject(subject, limit=20):
    try:
        response = supabase.table('questions').select("*").eq('subject', subject).execute()
        data = response.data
        if not data: return []
        
        if subject == "Оқу сауаттылығы":
            data.sort(key=lambda x: x.get('context', '') or '')
            selected = data[:limit]
        else:
            random.shuffle(data)
            selected = data[:limit]
        
        return [{
            "id": r["id"],
            "q": r["question"],
            "opts": json.loads(r["options"]),
            "a": r["answer"],
            "expl": r["explanation"],
            "context": r.get("context")
        } for r in selected]
    except Exception as e:
        print(f"Сұрақ алу қатесі: {e}")
        return []

def get_my_results(user_id):
    try:
        response = supabase.table('results').select("*").eq('user_id', user_id).order('id', desc=True).execute()
        return response.data
    except: return []

# --- РЕЙТИНГ ЖҮЙЕСІ ---
def get_leaderboard_general():
    try:
        users_res = supabase.table('users').select("id, full_name").eq('role', 'student').execute()
        users = users_res.data
        
        results_res = supabase.table('results').select("user_id, subject, score").eq('is_active', True).execute()
        results = results_res.data

        leaderboard = []
        for u in users:
            uid = u['id']
            user_results = [r for r in results if r['user_id'] == uid]
            total_score = sum(r['score'] for r in user_results)
            
            # Әр пән бойынша балдарды есептеу
            hist = sum(r['score'] for r in user_results if r['subject'] == "Қазақстан тарихы")
            math_lit = sum(r['score'] for r in user_results if r['subject'] == "Математикалық сауаттылық")
            read = sum(r['score'] for r in user_results if r['subject'] == "Оқу сауаттылығы")
            math = sum(r['score'] for r in user_results if r['subject'] == "Математика") # ЖАҢА
            inf = sum(r['score'] for r in user_results if r['subject'] == "Информатика") # ЖАҢА
            
            if total_score > 0:
                leaderboard.append({
                    "full_name": u['full_name'],
                    "history": hist,
                    "math_lit": math_lit, 
                    "reading": read,
                    "math1": math,       
                    "inf": inf,          
                    "total_score": total_score
                })
        
        leaderboard.sort(key=lambda x: x['total_score'], reverse=True)
        return leaderboard
    except Exception as e: 
        print(f"Leaderboard Error: {e}")
        return []

def get_user_stats(user_id):
    try:
        res_count = supabase.table('results').select("id", count="exact").eq('user_id', user_id).execute()
        total_tests = res_count.count
        
        res_scores = supabase.table('results').select("score, total").eq('user_id', user_id).execute()
        if not res_scores.data: return 0, 0
            
        percentages = [(r['score'] / r['total'] * 100) for r in res_scores.data if r['total'] > 0]
        avg_score = sum(percentages) / len(percentages) if percentages else 0
        return total_tests, avg_score
    except: return 0, 0

# --- МҰҒАЛІМ ФУНКЦИЯЛАРЫ ---
def get_all_questions_for_teacher():
    try:
        response = supabase.table('questions').select("id, subject, question").order('id', desc=True).execute()
        return response.data
    except: return []

def delete_question(question_id):
    try:
        supabase.table('questions').delete().eq('id', question_id).execute()
        return True
    except Exception as e:
        print(f"Өшіру қатесі: {e}")
        return False

def add_question(subject, question, opts, answer, explanation=""):
    try:
        supabase.table('questions').insert({
            "subject": subject,
            "question": question,
            "options": json.dumps(opts),
            "answer": answer,
            "explanation": explanation,
            "context": None 
        }).execute()
        return True
    except: return False

def clear_leaderboard():
    try:
        supabase.table('results').update({"is_active": False}).gt('id', -1).execute()
        return True
    except: return False

# --- КІЛТ СӨЗ ЖӘНЕ ПАРОЛЬДІ ҚАЛПЫНА КЕЛТІРУ ---
def get_current_secret():
    try:
        response = supabase.table('settings').select("secret_key").eq('id', 1).execute()
        if response.data:
            return response.data[0]['secret_key']
    except: pass
    return "mektep2026"

def update_secret_key(new_key):
    try:
        supabase.table('settings').update({"secret_key": new_key}).eq('id', 1).execute()
        return True
    except: return False

def reset_password_with_key(username, new_password, input_key):
    ACTUAL_SECRET = get_current_secret()
    if input_key != ACTUAL_SECRET:
        return False, "Құпия кілт сөз қате!"

    try:
        user_check = supabase.table('users').select("id").eq('username', username).execute()
        if not user_check.data:
            return False, "Мұндай логин табылмады!"

        supabase.table('users').update({"password": new_password}).eq('username', username).execute()
        return True, "Құпия сөз сәтті өзгертілді!"
    except:
        return False, "Байланыс қатесі!"

# --- ӘКІМШІ (ADMIN) ФУНКЦИЯЛАРЫ ---
def get_all_users():
    try:
        response = supabase.table('users').select("id, full_name, username, password, role").order('id', desc=True).execute()
        return response.data
    except Exception as e:
        print(f"Users алу қатесі: {e}")
        return []

def update_user_info(user_id, new_username, new_password, new_fullname, new_role):
    try:
        data = {
            "username": new_username,
            "password": new_password,
            "full_name": new_fullname,
            "role": new_role 
        }
        supabase.table('users').update(data).eq('id', user_id).execute()
        return True
    except Exception as e:
        print(f"Update қатесі: {e}")
        return False

def delete_user(user_id):
    try:
        supabase.table('users').delete().eq('id', user_id).execute()
        return True
    except Exception as e:
        print(f"Delete user қатесі: {e}")
        return False
# --- ОНЛАЙН ДУЭЛЬ ФУНКЦИЯЛАРЫ ---

def create_battle(user_id, subject, room_name):
    """Жаңа ойын бөлмесін құру (Атауымен)"""
    try:
        data = {
            "player1_id": user_id,
            "subject": subject,
            "room_name": room_name, # Жаңа өріс
            "status": "waiting",
            "p1_score": 0,
            "p2_score": 0
        }
        response = supabase.table('battles').insert(data).execute()
        return response.data[0]
    except Exception as e:
        print(f"Create Battle Error: {e}")
        return None
def get_open_battles(subject):
    """Бос бөлмелерді іздеу"""
    try:
        # Статусы 'waiting' және пәні сәйкес келетін бөлмелер
        response = supabase.table('battles').select("*").eq('status', 'waiting').eq('subject', subject).execute()
        return response.data
    except: return []

def join_battle(battle_id, user_id):
    """Бар бөлмеге қосылу"""
    try:
        data = {
            "player2_id": user_id,
            "status": "active" # Ойын басталды деп белгілейміз
        }
        supabase.table('battles').update(data).eq('id', battle_id).execute()
        return True
    except: return False

def get_battle_status(battle_id):
    """Ойын күйін және ұпайларды алу (секунд сайын тексеру үшін)"""
    try:
        response = supabase.table('battles').select("*").eq('id', battle_id).execute()
        if response.data:
            return response.data[0]
    except: pass
    return None

def update_battle_score(battle_id, player_num, score):
    """Ұпайды жаңарту (player_num = 1 немесе 2)"""
    try:
        field = "p1_score" if player_num == 1 else "p2_score"
        supabase.table('battles').update({field: score}).eq('id', battle_id).execute()
    except: pass
# --- database.py соңына қосыңыз ---

def delete_battle(battle_id):
    """Бөлмені өшіру (Күту режимінен шыққанда)"""
    try:
        supabase.table('battles').delete().eq('id', battle_id).execute()
        return True
    except Exception as e:
        print(f"Delete battle error: {e}")
        return False
# --- ЖАРЫСТАР (CONTESTS) ФУНКЦИЯЛАРЫ ---

# database.py ішіне қосыңыз:

def create_contest(title, description):
    try:
        # Debug үшін консольге шығарамыз
        print(f"Жарыс құрылуда: {title}")
        
        supabase.table('contests').insert({
            "title": title,
            "description": description,
            "is_active": True
        }).execute()
        
        print("Сәтті құрылды!")
        return True
    except Exception as e:
        print(f"Жарыс құру қатесі: {e}") # Қате кодын көру үшін
        return False

def add_contest_question(contest_id, question, opts, answer):
    """Жарысқа сұрақ қосу (Админ)"""
    try:
        supabase.table('contest_questions').insert({
            "contest_id": contest_id,
            "question": question,
            "options": json.dumps(opts),
            "answer": answer
        }).execute()
        return True
    except: return False

def get_all_contests_for_student():
    """Оқушыға барлық жарыстарды көрсету (Ашық және Жабық)"""
    try:
        # .eq('is_active', True) дегенді алып тастадық
        response = supabase.table('contests').select("*").order('id', desc=True).execute()
        return response.data
    except: return []
def get_contest_questions(contest_id):
    """Жарыс сұрақтарын алу"""
    try:
        response = supabase.table('contest_questions').select("*").eq('contest_id', contest_id).execute()
        data = response.data
        if not data: return []
        # Форматтау
        return [{
            "id": r["id"],
            "q": r["question"],
            "opts": json.loads(r["options"]),
            "a": r["answer"],
            "expl": "" # Жарыста түсіндірме болмайды
        } for r in data]
    except: return []

def save_contest_result(contest_id, user_id, score, total):
    """Нәтижені сақтау"""
    try:
        # Егер бұрын тапсырған болса, нәтижені жаңартпаймыз (Бір рет қана тапсыру)
        check = supabase.table('contest_results').select("*").eq('contest_id', contest_id).eq('user_id', user_id).execute()
        if check.data:
            return False # Қайта тапсыруға болмайды
            
        supabase.table('contest_results').insert({
            "contest_id": contest_id,
            "user_id": user_id,
            "score": score,
            "total": total
        }).execute()
        return True
    except: return False

def get_contest_leaderboard(contest_id):
    """Нақты жарыстың рейтингі"""
    try:
        # Нәтижелерді аламыз
        res = supabase.table('contest_results').select("*").eq('contest_id', contest_id).order('score', desc=True).execute()
        results = res.data
        
        # Оқушылардың атын алу үшін ID-ларды жинаймыз
        user_ids = [r['user_id'] for r in results]
        if not user_ids: return []
        
        users_res = supabase.table('users').select("id, full_name").in_('id', user_ids).execute()
        users_map = {u['id']: u['full_name'] for u in users_res.data}
        
        leaderboard = []
        for r in results:
            leaderboard.append({
                "full_name": users_map.get(r['user_id'], "Белгісіз"),
                "score": r['score'],
                "total": r['total']
            })
        return leaderboard
    except: return []
# --- DATABASE.PY СОҢЫНА ҚОСЫҢЫЗ ---

# --- database.py СОҢЫНА ҚОСЫҢЫЗ ---

# 1. Админ: Барлық жарыстарды алу
def get_all_contests_admin():
    try:
        # id бойынша сұрыптаймыз (жаңасы жоғарыда)
        response = supabase.table('contests').select("*").order('id', desc=True).execute()
        return response.data
    except: return []

# 2. Админ: Жарысты өшіру
def delete_contest(contest_id):
    try:
        # Алдымен сұрақтарын, кейін жарыстың өзін өшіру (егер cascade жоқ болса)
        supabase.table('contest_questions').delete().eq('contest_id', contest_id).execute()
        supabase.table('contest_results').delete().eq('contest_id', contest_id).execute()
        supabase.table('contests').delete().eq('id', contest_id).execute()
        return True
    except Exception as e:
        print(e)
        return False

# 3. Админ: Статусын өзгерту (Ашық/Жабық)
def update_contest_status(contest_id, is_active):
    try:
        supabase.table('contests').update({"is_active": is_active}).eq('id', contest_id).execute()
        return True
    except: return False

# 4. Админ: Жарысқа сұрақ қосу
def add_contest_question(contest_id, question, opts, answer):
    try:
        supabase.table('contest_questions').insert({
            "contest_id": contest_id,
            "question": question,
            "options": json.dumps(opts),
            "answer": answer
        }).execute()
        return True
    except: return False

# 5. Админ: Жарыс сұрағын өшіру
def delete_contest_question(question_id):
    try:
        supabase.table('contest_questions').delete().eq('id', question_id).execute()
        return True
    except: return False

# 6. Оқушы: Қатысқанын тексеру (Қайта кіргізбеу үшін)
def check_participation(user_id, contest_id):
    try:
        response = supabase.table('contest_results').select("id").eq('user_id', user_id).eq('contest_id', contest_id).execute()
        return len(response.data) > 0 # Егер тізім бос болмаса, демек қатысқан
    except: return False
# database.py соңына қосыңыз:

# --- ЧАТ ФУНКЦИЯЛАРЫ ---
def send_global_message(user_id, username, message):
    try:
        supabase.table('global_chat').insert({
            "user_id": user_id,
            "username": username,
            "message": message
        }).execute()
        return True
    except Exception as e:
        print(f"Error sending message: {e}")
        return False

def get_last_messages(limit=50):
    try:
        # Ең соңғы 50 хабарламаны аламыз (уақыты бойынша сұрыптау)
        response = supabase.table('global_chat').select("*").order("created_at", desc=True).limit(limit).execute()
        # Тізімді кері аударамыз (ескісі жоғарыда, жаңасы төменде тұруы үшін)
        return response.data[::-1] if response.data else []
    except Exception as e:
        print(f"Error getting messages: {e}")
        return []
# database.py соңына:

# Чаттың құлыптаулы екенін тексеру
def is_chat_locked():
    try:
        response = supabase.table('app_settings').select("value").eq("key", "chat_locked").execute()
        if response.data:
            return response.data[0]['value'] == 'true'
        return False
    except:
        return False

# Чатты құлыптау немесе ашу (Тек Админ үшін)
def toggle_chat_lock(lock_status):
    try:
        val = 'true' if lock_status else 'false'
        supabase.table('app_settings').update({"value": val}).eq("key", "chat_locked").execute()
        return True
    except:
        return False
# --- database.py СОҢЫНА ҚОСЫҢЫЗ ---

# 1. Админ: Барлық жарысты алу (Жабық/Ашық бәрін)
def get_all_contests_for_admin():
    try:
        res = supabase.table('contests').select("*").order('created_at', desc=True).execute()
        return res.data
    except: return []

# 2. Админ: Жарысты өшіру (Сұрақтарымен бірге)
def delete_contest(contest_id):
    try:
        # Алдымен осы жарыстың сұрақтарын өшіреміз (Foreign Key қатесін болдырмау үшін)
        supabase.table('contest_questions').delete().eq('contest_id', contest_id).execute()
        # Нәтижелерді де өшіреміз
        supabase.table('contest_results').delete().eq('contest_id', contest_id).execute()
        # Сосын жарыстың өзін өшіреміз
        supabase.table('contests').delete().eq('id', contest_id).execute()
        return True
    except Exception as e:
        print(e)
        return False

# 3. Админ: Статусын өзгерту (Ашық/Жабық)
def update_contest_status(contest_id, is_active):
    try:
        supabase.table('contests').update({"is_active": is_active}).eq('id', contest_id).execute()
        return True
    except: return False

# 4. Админ: Жарысқа сұрақ қосу
def add_contest_question(contest_id, question, opts, answer):
    try:
        supabase.table('contest_questions').insert({
            "contest_id": contest_id,
            "question": question,
            "options": json.dumps(opts), # Опцияларды JSON қылып сақтаймыз
            "answer": answer
        }).execute()
        return True
    except: return False

# 5. Админ: Жарыс сұрағын өшіру
def delete_contest_question(question_id):
    try:
        supabase.table('contest_questions').delete().eq('id', question_id).execute()
        return True
    except: return False
