# Semantle Hebrew Solver (סמענטל)

Deployment - https://smental-solver.vercel.app/

אלגוריתם אוטומטי לפתרון המשחק היומי **סמענטל** בעברית באמצעות מודל וקטורים סמנטיים (FastText), מנוע צירוף ליניארי ממושקל (Vector Gravity) ומנגנון דחייה אקטיבי (Active Repulsion).

בבנייה כעת: לוח ויזואליזציה תלת-ממדי חי שמציג את תהליך החיפוש בזמן אמת.
האפיון: [docs/superpowers/specs/2026-09-18-semantle-live-board-design.md](docs/superpowers/specs/2026-09-18-semantle-live-board-design.md)

## תכונות עיקריות

- Vector Gravity Search: חישוב וקטור יעד משוער באמצעות שילוב אקספוננציאלי ממושקל של ציוני העוגנים.
- Active Repulsion: זיהוי והתרחקות מאזורים סמנטיים תקועים למניעת הסתובבות בלולאה.
- Smart Stemming & Deduplication: סינון הטיות דקדוקיות כפולות למניעת בזבוז קריאות API.
- Dynamic Focused Exploitation: הקשחת רדיוס החיפוש ברגע שנחשפת מילה בציון גבוה.
- Rate-Limit Resilient: ניהול Session רציף עם טיפול חסום בשגיאות עומס (429).
- מנוע מבוסס אירועים: המנוע פולט אירועים במקום להדפיס, כך שאותה לוגיקה משרתת את הטרמינל ואת הלוח.

## מבנה הפרויקט

- `solver/` — מנוע הפתרון. לוגיקה טהורה: לא מדפיס, לא יודע על רשת ולא על תצוגה
  - `config.py` — פרמטרים, ספים ורשימת עוגנים
  - `morphology.py` — סינון עברית, גזירת שורש וזיהוי כפילויות
  - `vocabulary.py` — טעינת ארטיפקט אוצר המילים
  - `events.py` — טיפוסי האירועים שהמנוע פולט
  - `engine.py` — אלגוריתם החיפוש, כגנרטור
- `semantle/client.py` — תקשורת מול ה-API של המשחק
- `server/projection.py` — המרת וקטור 300-ממדי למיקום על הלוח
- `cli/` — הצגה בטרמינל (`runner.py`) והגרף המסכם (`plotting.py`)
- `scripts/` — כלים חד-פעמיים: בניית אוצר המילים ומדידת ההקרנה
- `tests/` — בדיקות
- `run_cli.py` — נקודת כניסה

## התקנה והרצה

1. התקנת תלויות:

   ```
   pip install -r requirements.txt
   ```

2. הבאת אוצר המילים הבנוי (26MB):

   ```
   python -m scripts.fetch_vocab
   ```

   הקובץ אינו נשמר בגיט — בינארי בגודל כזה היה נשאר בהיסטוריה לנצח, וכל
   בנייה מחדש הייתה מוסיפה עותק. הוא מתפרסם כנכס של GitHub Release ונמשך
   בזמן ההתקנה. אותה פקודה משמשת גם כשלב build בפריסה.

   כדי לבנות אותו מחדש מהמקור במקום להוריד (למשל אחרי שינוי בפילטר
   המילים), צריך את מודל FastText המלא:

   ```
   curl -L -o data/wiki.he.vec https://dl.fbaipublicfiles.com/fasttext/vectors-wiki/wiki.he.vec
   python -m scripts.build_vocab
   ```

4. הרצת הפותר בטרמינל:

   ```
   python run_cli.py
   ```

5. הרצת הבדיקות:

   ```
   python -m pytest
   ```

## הלוח

האתר סטטי. משימה מתוזמנת ([.github/workflows/daily-solve.yml](.github/workflows/daily-solve.yml))
פותרת את מילת היום כמה פעמים ביום ומפרסמת את הריצה כקובץ
`web/public/daily.json`; הדף טוען אותו ישירות, כך שאין שרת שצריך להמתין לו
ו-Semantle שומע מהפרויקט כמה פעמים ביום במקום פעם לכל מבקר. לפני כל ריצה
המשימה שואלת בקריאה אחת האם המילה השמורה עדיין מחזירה 100, ואם כן אינה
עושה דבר.

```
npm --prefix web install
npm --prefix web run dev
```

### לצפות בחיפוש אמיתי בזמן אמת

השרת לא נדרש לאתר, אבל הוא קיים כדי לראות את הפותר עובד מול המשחק:

```
python -m uvicorn server.app:app --port 8000     # טרמינל ראשון
npm --prefix web run dev                          # טרמינל שני
```

ובנוסף `web/.env.local` עם `VITE_LIVE_SOLVER=true` (ראה `web/.env.example`).

### לפרסם ריצה ידנית

```
python -m scripts.publish_daily
```


cd C:\VScdoeProjects\Smental_Solver
python -m uvicorn server.app:app --port 8000

cd C:\VScdoeProjects\Smental_Solver\web
npm run dev
