Процесор-бот, який бере сповіщення з сігнал-групи, вицмикує звідти аттачменти
1. Зберігає їх у відповідній папочці - YYYY/MM/dd.mm.yyyy/орігінальни_файл
2. Дивиться в док або пдф за інформацією СЧЗшничка, збирає у відповідний обʼєкт
3. Шукає СЗЧшничка в екселі, (ПІБ+ДатаНародження+РНКОПП)
    а. якщо знайшов, додає бракуючу інформацію (часто - дата возврату)
    б. якщо не знайшов, додає нову строчку і заповнює всі відповідні стовпчики
4. А далі ручками, друзі, ручками.

В проекті також є можливість працювати через меню. 
Для цього наберіть "меню" в особистому чаті. 
1. Батч процессор всіх файлів за сьогодні (бажано запускати до 16, або скільки там налаштовано у вас)
2. Конверсія та доповнення полів на базі інфо з БІО


Технічні дані:

Number for bot:: +38093 8513200

# Signal

**run copy of signal 2 on mac:**

```jsx
/Applications/Signal.app/Contents/MacOS/Signal --user-data-dir="$HOME/Library/Application Support/Signal-2”
```

або 

```jsx
cd ~ && /Applications/Signal.app/Contents/MacOS/Signal --user-data-dir="$HOME/Library/Application Support/Signal 2”
```

**run signal daemon:**

```jsx
jenv local 21
signal-cli -u +380938513200 daemon --socket /tmp/signal-bot.sock
or
signal-cli -u +380938513200 daemon --tcp 127.0.0.1:1234 

```

Network configuration is in the env file.
Pls take a look at .env_example

Link device with following instructions: https://gemini.google.com/app/60bae3eb3c68ebd9

Видаляємо всі старі налаштування

```jsx
rm -rf ~/.local/share/signal-cli
```

Створюємо чисту папку заново

```jsx
mkdir -p ~/.local/share/signal-cli
```

python3 [bot.py](http://bot.py/)

Additional packages

python-docx (1.2.0)

```jsx
python3 -m pip install python-docx
```

Щоб ця хрінь заработала нормально, для півот-таблиць треба потанцювати з бубліком:
1. Правою кнопкою на PivotTable -> PivotTable Options (Параметри зведеної таблиці).
2. Вкладка Data (Дані).
3. Зніміть галочку з пункту "Save source data with file" (Зберігати вихідні дані разом із файлом).

Не забувайте час від часу піджигати тестіки! Вони повинні бути зелененькими!
