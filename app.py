from flask import Flask, redirect, session, url_for, g, request, render_template_string

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Replace with your secret key

# Mock database of users
mock_users = {
    "mock_user": {"userinfo": {"name": "Mock User", "email": "mock@example.com"}, "password": "password123"}
}

# Authentication check decorator
def login_required(f):
    def decorated_function(*args, **kwargs):
        if not g.user:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@app.before_request
def load_logged_in_user():
    user = session.get('user')
    g.user = user if user else None

@app.route("/")
def start():
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = mock_users.get(username)
        
        # Check if user exists and password matches
        if user and user.get("password") == password:
            session["user"] = user
            return redirect(url_for("home"))
        else:
            return "Invalid Credentials", 401

    # Simulated login form
    return render_template_string('''
        <h1>Login</h1>
        <form method="post">
            <label for="username">Username:</label>
            <input type="text" id="username" name="username"><br>
            <label for="password">Password:</label>
            <input type="password" id="password" name="password"><br>
            <input type="submit" value="Login">
        </form>
    ''')

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/home")
@login_required
def home():
    user_to_show = g.user['userinfo']['name']
    return f"<h1>Hello {user_to_show}</h1>"

if __name__ == "__main__":
    app.run(debug=True)