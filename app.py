import math
import re
from html import escape
from pathlib import Path

from flask import Flask, request

app = Flask(__name__)
PAGE = Path(__file__).with_name("index.html").read_text(encoding="utf-8")
NUMBER_AT_END = re.compile(r"(?:\d+(?:\.\d*)?|\.\d+)$")


def calculate(expression):
    if len(expression) > 100:
        raise ValueError("Invalid expression")

    expression = re.sub(r"(\d+(?:\.\d*)?|\.\d+)%", r"(\1/100)", expression)
    if not re.fullmatch(r"[0-9.+*/()\-\s]+", expression):
        raise ValueError("Invalid expression")
    if "**" in expression or "//" in expression:
        raise ValueError("Invalid expression")

    try:
        result = eval(expression, {"__builtins__": {}}, {})
    except ZeroDivisionError:
        raise ValueError("Cannot divide by zero") from None
    except (SyntaxError, OverflowError):
        raise ValueError("Invalid expression") from None
    if not math.isfinite(result):
        raise ValueError("Invalid expression")
    return result


def press(expression, key):
    if key.isdigit():
        if re.search(r"(^|[+\-*/])0$", expression):
            return expression[:-1] + key
        return expression + key

    elif key in ("+", "-", "*", "/"):
        if expression and expression[-1] in "+-*/":
            return expression[:-1] + key
        if expression or key == "-":
            return expression + key
        return expression

    elif key == "decimal":
        match = NUMBER_AT_END.search(expression.rstrip("+-*/"))
        if match and "." in match.group():
            return expression
        return expression + ("." if expression and expression[-1].isdigit() else "0.")

    elif key == "%" and expression and expression[-1].isdigit():
        return expression + "%"

    elif key == "backspace":
        return expression[:-1]

    elif key == "clear":
        return NUMBER_AT_END.sub("", expression).rstrip("+-*/")

    elif key == "sign":
        match = NUMBER_AT_END.search(expression)
        if not match:
            return "-" if not expression else expression
        prefix, number = expression[:match.start()], match.group()
        if prefix.endswith("-") and (len(prefix) == 1 or prefix[-2] in "+-*/("):
            return prefix[:-1] + number
        return prefix + "-" + number
    return expression


def render(expression="", previous="", done=False, theme="dark", error=""):
    shown = (previous or expression).replace("*", "×").replace("/", "÷").replace("-", "−")
    if previous:
        shown += " ="

    if error:
        result = error
    elif done:
        result = expression
    else:
        match = NUMBER_AT_END.search(expression.rstrip("+-*/"))
        result = match.group() if match else "0"

    values = {
        "theme_class": "light" if theme == "light" else "",
        "expression": expression,
        "completed_expression": previous,
        "done": "1" if done else "0",
        "theme": theme,
        "theme_label": "Dark mode" if theme == "light" else "Light mode",
        "shown_expression": shown,
        "result": result,
        "result_class": "error" if error else "",
    }
    page = PAGE
    for name, value in values.items():
        page = page.replace("{{" + name + "}}", escape(value, quote=True))
    return page


@app.route("/", methods=["GET", "POST"])
def calculator():
    form = request.form
    expression = form.get("expression", "")
    previous = form.get("completed_expression", "")
    done = form.get("done") == "1"
    theme = form.get("theme", "dark")
    key = form.get("key", "")
    error = ""

    if form.get("action") == "toggle-theme":
        theme = "dark" if theme == "light" else "light"
    elif key == "all-clear":
        expression, previous, done = "", "", False
    else:
        if done and key not in ("", "equals"):
            if key.isdigit() or key == "decimal":
                expression = ""
            previous, done = "", False
        if key == "equals" and expression:
            try:
                value = calculate(expression)
                previous = expression
                expression = format(value, ".10g")
                done = True
            except ValueError as exception:
                error = str(exception)
        else:
            expression = press(expression, key)

    return render(expression, previous, done, theme, error)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000)
