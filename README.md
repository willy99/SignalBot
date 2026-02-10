The bot processor, gets messages from Signal group, download attachment, parses doc, docx, pdf and create a corresponding record in the desertion excel file.


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

# Telegram

willy2005_test_bot

8516834870:AAHdkf7GVyUCSKuny9kwO1PlxOqyfdoeItE
