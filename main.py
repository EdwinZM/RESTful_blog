from flask import Flask, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import query, relation, relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar
from sqlalchemy import ForeignKey

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)


##CONFIGURE TABLES

class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.String(250), db.ForeignKey("users.name"), nullable=False)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.String(), nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    authors = relationship("Users", back_populates="posts")
    comments = relationship("Comment", back_populates="post_comments")

class Users(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), nullable = False)
    email = db.Column(db.String(250), nullable = False)
    password = db.Column(db.String(250), nullable = False)
    posts = relationship("BlogPost", back_populates="authors")
    comments = relationship("Comment", back_populates="author")

class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(), nullable = False)
    author = relationship("Users", back_populates = "comments")
    comment_author = db.Column(db.String(), db.ForeignKey("users.name"))
    post_comments = relationship("BlogPost", back_populates= "comments")
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    
    
db.create_all()

@login_manager.user_loader
def load_user(user_id):
    print(user_id)
    return Users.query.get(user_id)


@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts, current_user = current_user)


@app.route('/register', methods=["POST", "GET"])
def register():
    form = RegisterForm()
    error = None

    if request.method == "POST":

        if form.validate_on_submit():
            
            name = form.name.data
            email = form.email.data
            password = form.password.data

            password = generate_password_hash(password)

            new_user = Users(name=name, email=email, password=password)

            users = Users.query.all()

            for user in users:
                if user.email == email:
                    error = "User already Exist"
                    return render_template("register.html", form = form, error = error)
            
            db.session.add(new_user)
            db.session.commit()

            login_user(new_user)

            return redirect("/")

    return render_template("register.html", form=form, error=error)


@app.route('/login', methods=["POST", "GET"])
def login():
    form  = LoginForm()

    error = None

    if request.method == "POST":
        if form.validate_on_submit():
            email = form.email.data
            password = form.password.data

            users = Users.query.all()

            for user in users:
                if user.email == email:
                    is_password = check_password_hash(user.password, password)

                    if is_password:
                        login_user(user)
                        return redirect("/")
                    else:
                        error = "Password is Incorrect!"
                        return render_template("login.html", error=error, form=form)
            

            error = "User Not Found!"

    return render_template("login.html", form = form, error = error)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")


@app.route("/post/<int:post_id>", methods=["POST", "GET"])
@login_required
def show_post(post_id):
    requested_post = BlogPost.query.get(post_id)
    form = CommentForm()
    comments = requested_post.comments
    if request.method == "POST":
        if form.validate_on_submit():
            new_comment = Comment(text = form.comment.data, comment_author = current_user.name, post_id = requested_post.id)
            db.session.add(new_comment)
            db.session.commit()
    return render_template("post.html", post=requested_post, form = form, comments = comments)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/new-post", methods=["POST", "GET"])
@login_required
def add_new_post():
    form = CreatePostForm()
    is_admin = False

    if current_user.id == 1:
        is_admin = True

    if is_admin:
        if request.method == "POST":
            if form.validate_on_submit():
                new_post = BlogPost(
                    title=form.title.data,
                    subtitle=form.subtitle.data,
                    body=form.body.data,
                    img_url=form.img_url.data,
                    author=current_user.name,
                    date=date.today().strftime("%B %d, %Y")
                )
                db.session.add(new_post)
                db.session.commit()
                return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form, is_admin = is_admin)


@app.route("/edit-post/<int:post_id>", methods=["POST", "GET"])
@login_required
def edit_post(post_id):

    if current_user.id == 1:
        is_admin = True
    else:
        is_admin = False

    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        body=post.body
    )
    
    if request.method == "POST":
        if edit_form.validate_on_submit():
            post.title = edit_form.title.data
            post.subtitle = edit_form.subtitle.data
            post.img_url = edit_form.img_url.data
            post.author = current_user.name
            post.body = edit_form.body.data
            db.session.commit()
            return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form, is_admin = is_admin)


@app.route("/delete/<int:post_id>")
@login_required
def delete_post(post_id):

    if current_user.id == 1:
        post_to_delete = BlogPost.query.get(post_id)
        db.session.delete(post_to_delete)
        db.session.commit()
    else:
        flash("You need to be an admin to see this")

    print(current_user.id)


    return render_template('index.html')


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
