# Semantle Hebrew Solver (סמענטל)

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

2. הורדת מודל הוקטורים (1.23GB, לא נכנס לגיט):

   ```
   curl -L -o data/wiki.he.vec https://dl.fbaipublicfiles.com/fasttext/vectors-wiki/wiki.he.vec
   ```

3. בניית ארטיפקט אוצר המילים (פעם אחת, ממיר ל-26MB שנטענים מיידית):

   ```
   python -m scripts.build_vocab
   ```

4. הרצת הפותר:

   ```
   python run_cli.py
   ```

5. הרצת הבדיקות:

   ```
   python -m pytest
   ```
