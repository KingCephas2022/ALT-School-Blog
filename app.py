#IMPORTS python
import os

#IMPORTS flask
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
#from flask_migrate import Migrate
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

#IMPORTS sqlalch
from sqlalchemy.sql import func
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

#************************************************
#CONSTS AND VARS
#************************************************

base_dir = os.path.dirname(os.path.realpath(__file__))

#************************************************
#APP INITIALIZATION
#************************************************

app = Flask(__name__, template_folder='templates')
app.config["SQLALCHEMY_DATABASE_URI"]='sqlite:///' + os.path.join(base_dir, 'users.db')
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = '923054541f636448117274bc'

#************************************************
#ADDONS INITIALIZATION
#************************************************

db = SQLAlchemy(app)
login_manager = LoginManager(app)

#************************************************
#MODELS
#************************************************

class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True)
    username = db.Column(db.String(150), unique=True)
    password_hash = db.Column(db.Text(), nullable = False)
    first_name = db.Column(db.Text(), nullable = True)
    last_name = db.Column(db.Text(), nullable = True)
    date_created = db.Column(db.DateTime(timezone=True), default=func.now())

    def __repr__(self):
        return f"User {self.username}"

class Post(db.Model):
    __tablename__ = "posts"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable = False)
    title = db.Column(db.String(150), nullable = False)
    content = db.Column(db.String(150), nullable = True)
    date_posted = db.Column(db.DateTime(timezone=True), default=func.now())

    def __repr__(self):
        return f"Post {self.title}"

    def get_author(self):
        return User.query.filter(User.id==self.user_id).first()

    def get_author_header(self):
        author = User.query.filter(User.id==self.user_id).first()
        if author is not None:
            return author.username
        return "Unknown"

#************************************************
#UTILS
#************************************************

def response_on_fail(res_msg,error):
    flash(res_msg),
    flash(str(error))

#************************************************
#ROUTES AUTHENTICATION
#************************************************

@login_manager.user_loader
def user_loader(id):
    return User.query.get(int(id))

@app.route('/')
@app.route('/home')
def index():
    existing_posts = Post.query.all()
    return render_template('index.html',blog_posts=existing_posts)

@app.route("/about")
def about():
    return render_template('about.html')

@app.route("/contact")
def contact():
    return render_template('contact.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route("/login", methods=['GET', 'POST'])
def login():

    if request.method=="POST":
        try:
            email = request.form.get('email')
            password = request.form.get('password')

            user = User.query.filter_by(email=email).first()
            
            if user:
                if check_password_hash(user.password_hash, password):
                    flash("Logged in!", category='success')
                    login_user(user, remember=True)
                    return redirect(url_for('index'))
                else:
                    flash('Password is incorrect.', category='error')
            else:
                    flash('Email does not exist.', category='error')
        except Exception as e:
            response_on_fail("Login failed",e)
    return render_template('login.html')

@app.route("/sign-up", methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        try:
            first_name = request.form.get("first_name")
            last_name = request.form.get("last_name")
            email = request.form.get("email")
            username = request.form.get("username")
            password1 = request.form.get("password1")
            password2 = request.form.get("password2")

            email_exists = User.query.filter_by(email=email).first()
            username_exists = User.query.filter_by(username=username).first()

            if email_exists:
                flash('Email is already in use.', category='error')
            elif username_exists:
                flash('Username is already in use.', category='error')
            elif password1 != password2:
                flash('Password don\'t match!', category='error')
            elif len(username) < 2:
                flash('Username is too short.', category='error')
            elif len(password1) < 6:
                flash('Password is too short.', category='error')
            elif len(email) < 4:
                flash("Email is invalid.", category='error')
            else:
                new_user = User(
                    email=email, username=username, 
                    password_hash=generate_password_hash(
                        password1, method='sha256'
                    )
                )
                db.session.add(new_user)
                db.session.commit()
                login_user(new_user, remember=True)
                flash('User created!')
                return redirect(url_for("login"))
        except Exception as e:
            response_on_fail("Signup failed",e)
    return render_template('signup.html')

#************************************************
#ROUTES POST
#************************************************

@app.route("/post", methods=['GET','POST'])
@login_required
def post_create():
    if request.method =='POST':
        try:
            title = request.form.get('title')
            content = request.form.get('content')
            date_posted = datetime.utcnow()
            if "" in [title,content]:
                flash("Invalid input")
                return redirect(url_for('post'))

            title_exists = Post.query.filter_by(title=title).first()
            if title_exists:
                flash("Post with this title already exists")
                return redirect(url_for('post'))

            new_post = Post(
                user_id=int(current_user.id),
                title=title,
                content=content,
                date_posted=date_posted
            ) 

            db.session.add(new_post)
            db.session.commit()

            return redirect(url_for('index'))
        except Exception as e:
            response_on_fail("post creation failed",e)
    return render_template('post.html')

@app.route("/edit/<int:id>", methods=["GET", "POST"])
@login_required
def post_edit(id):

    try:
        blog_post = Post.query.filter(Post.id==int(id)).first()
        if blog_post == None:
            flash("Post not found")
            return redirect(url_for('index'))

        if int(current_user.id) == int(blog_post.user_id):
            if request.method == 'POST':

                blog_post.title = request.form['title']
                blog_post.content = request.form['content']
                db.session.add(blog_post)
                db.session.commit()

                flash("Heads up! Post edited")
                return redirect(url_for('index'))
        else:
            flash("Only the post author can edit the post")
    except Exception as e:
        response_on_fail("Post edit failed",e)
        return redirect(url_for('index'))
    return render_template('edit.html',blog_post=blog_post)

@app.route("/delete/<int:id>", methods=["GET", "POST"])
@login_required
def post_delete(id):

    try:
        blog_post = Post.query.filter(Post.id==int(id)).first()
        if blog_post == None:
            flash("Post not found")
            return redirect(url_for('index'))

        if int(current_user.id) == int(blog_post.user_id):
            db.session.delete(blog_post)
            db.session.commit()
            flash("Post deleted")
        else:
            flash("Only the post author can delete the post")
    except Exception as e:
        response_on_fail("Post delete failed",e)
    return redirect(url_for('index'))

if __name__ == '__main__':
        app.run(debug=True)
