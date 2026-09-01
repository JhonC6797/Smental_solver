# Semantle Hebrew Solver (סמענטל)

אלגוריתם אוטומטי לפתרון המשחק היומי **סמענטל** בעברית באמצעות מודל וקטורים סמנטיים (FastText), מנוע צירוף ליניארי ממושקל (Vector Gravity) ומנגנון דחייה אקטיבי (Active Repulsion).

## תכונות עיקריות

- Vector Gravity Search: חישוב וקטור יעד משוער באמצעות שילוב אקספוננציאלי ממושקל של ציוני העוגנים.
- Active Repulsion: זיהוי והתרחקות מאזורים סמנטיים תקועים למניעת בלבלות בלולאה.
- Smart Stemming & Deduplication: ניקוי וסינון הטיות דקדוקיות כפולות למניעת בזבוז קריאות API.
- Dynamic Focused Exploitation: הקשחת רדיוס החיפוש ברגע שנחשפת מילה בציון גבוה (60%+).
- Rate-Limit Resilient: ניהול Session רציף עם טיפול אוטומטי בשגיאות עומס (429).

## מבנה הפרויקט

- config.py: הגדרות מערכת, פרמטרים ורשימת עוגנים
- api_client.py: ניהול תקשורת מול ה-API של סמענטל
- model_loader.py: טעינה ונירמול מודל הוקטורים המקומי
- utils.py: עיבוד טקסט, ניקוי וסינון מורפולוגי
- solver.py: מנוע החישוב הווקטורי, המשיכה והדחייה
- main.py: נקודת ההפעלה המרכזית

## התקנה והרצה

1. שיבוט המאגר:
   git clone https://github.com/JhonC6797/Smental_solver.git
   cd Smental_solver

2. הקמת סביבה וירטואלית והתקנת תלויות:
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt

3. הורדת מודל הוקטורים:
   יש להוריד את קובץ הוקטורים העברי wiki.he.vec ממאגר FastText ולמקם אותו בתיקיית השורש.

4. הרצת הפותר:
   python main.py
