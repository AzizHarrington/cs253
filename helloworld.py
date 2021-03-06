import os
import webapp2
import jinja2
import json
import funcs
import logging
from datetime import datetime
from google.appengine.api import memcache
from google.appengine.ext import db

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir),
                               autoescape=True)


def render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)


class BaseHandler(webapp2.RequestHandler):

    def render(self, template, **kw):
        self.response.out.write(render_str(template, **kw))

    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def read_secure_cookie(self, name):
        cookie_val = self.request.cookies.get(name)
        return cookie_val and self.check_secure_val(cookie_val)

    def check_secure_val(self, secure_val):
        val = secure_val.split("|")
        user_id = val[0]
        hashbrowns = val[-1]
        if user_id:
            u = User.get_by_id(int(user_id))
            if u:
                if u.password == hashbrowns:
                    return user_id

    def initialize(self, *a, **kw):
        webapp2.RequestHandler.initialize(self, *a, **kw)
        uid = self.read_secure_cookie('user_id')
        self.user = uid and User.get_by_id(int(uid))


class MainPage(BaseHandler):

    def get(self):
        self.render("main.html")


class Birthday(BaseHandler):

    def get(self):
        self.render('birthday.html')

    def post(self):
        user_month = self.request.get('month')
        user_day = self.request.get('day')
        user_year = self.request.get('year')

        month = funcs.valid_month(user_month)
        day = funcs.valid_day(user_day)
        year = funcs.valid_year(user_year)

        if not (month and day and year):
            self.render("birthday.html", error="That doesn't look valid to me, friend.",
                        month=user_month, day=user_day, year=user_year)
        else:
            self.redirect("/thanks")


class Thanks(BaseHandler):

    def get(self):
        self.write("Thanks! That's a totally valid day!")


class Rot13(BaseHandler):

    def get(self):
        self.render('rot13.html')

    def post(self):
        rot13 = ''
        text = self.request.get('text')
        if text:
            rot13 = funcs.rot13(text)
        self.render('rot13.html', text=rot13)


class User(db.Model):

    username = db.StringProperty(required=True)
    password = db.StringProperty(required=True)
    salt = db.StringProperty(required=True)
    email = db.StringProperty()


class SignUp(BaseHandler):

    def get(self):
        self.render('signup.html')

    def post(self):
        have_error = False
        username = self.request.get('username')
        password = self.request.get('password')
        verify = self.request.get('verify')
        email = self.request.get('email')

        params = dict(username=username, email = email)

        users = db.GqlQuery("SELECT * FROM User")

        for user in users:
            if user.username == username:
                params['exist_error'] = "That username already exists."
                have_error = True

        if not funcs.valid_username(username):
            params['error_username'] = "That's not a valid username."
            have_error = True

        if not funcs.valid_password(password):
            params['error_password'] = "That's not a valid password."
            have_error = True
        elif password != verify:
            params['error_verify'] = "Those passwords don't match."
            have_error = True

        if not funcs.valid_email(email):
            params['error_email'] = "That's not a valid email."
            have_error = True

        if have_error:
            self.render('signup.html', **params)
        else:
            salted_password = funcs.make_pw_hash(username, password)
            u = User(username=username,
                     password=salted_password[0],
                     salt=salted_password[1],
                     email=email)
            u.put()
            u_id = u.put().id()

            self.response.headers.add_header('Set-Cookie',
                                             'user_id=%s|%s; Path=/' % (u_id, salted_password[0]))
            self.redirect('/blog/welcome')


class Login(BaseHandler):

    def get(self):
        self.render('login.html')

    def post(self):
        username = self.request.get("username")
        password = self.request.get("password")

        users = db.GqlQuery("SELECT * FROM User")

        for user in users:
            if user.username == username:
                h = [user.password, user.salt]
                if funcs.valid_pw(username, password, h):
                    self.response.headers.add_header('Set-Cookie',
                                                     'user_id=%s|%s; Path=/' % (str(user.key().id()), str(user.password)))
                    self.redirect('/blog/welcome')
        self.render('login.html', error='Login invalid.')


class Logout(BaseHandler):

    def get(self):
        self.response.headers.add_header('Set-Cookie', 'user_id=; Path=/')
        self.redirect('/blog')


class Welcome(BaseHandler):

    def get(self):
        user_id_cookie = self.request.cookies.get('user_id').split('|')
        user_id = user_id_cookie[0]
        hashbrowns = user_id_cookie[-1]

        if user_id:
            u = User.get_by_id(int(user_id))
            if u:
                if u.password == hashbrowns:
                    self.render("welcome.html", user=u.username)
        else:
            self.redirect('/blog/signup')


class Blog(db.Model):

    subject = db.StringProperty(required=True)
    content = db.TextProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)
    last_modified = db.DateTimeProperty(auto_now=True)

    def render(self):
        self._render_text = self.content.replace('\n', '<br>')
        return render_str("post.html", p=self)


def top_blogs(update=False):
    key = 'top'
    blogs = memcache.get(key)
    if blogs is None or update:
        logging.error("DB QUERY")
        time_now = datetime.now()
        blogs = db.GqlQuery("SELECT * FROM Blog ORDER BY created DESC")
        # prevent the running of multiple queries by storing in list
        blogs = list(blogs)
        blogs = (blogs, time_now)
        memcache.set(key, blogs)
    return blogs


class FlushCache(BaseHandler):

    def get(self):
        memcache.flush_all()
        self.redirect('/blog')


class BlogFront(BaseHandler):

    def get(self):
        blogs = top_blogs()[0]
        start = top_blogs()[1]
        end = datetime.now()
        diff = end - start
        time_passed = int(round(diff.total_seconds()))
        self.render("front.html",
                    blogs=blogs,
                    time_passed=time_passed,
                    user=self.user)


class BlogFrontJSON(BaseHandler):

    def get(self):
        self.response.headers['Content-Type'] = 'application/json'

        blogs = top_blogs()[0]
        blog_list = []

        for blog in blogs:
            subject = blog.subject
            content = blog.content
            created = blog.created.strftime("%a, %d %b %Y")
            last_modified = blog.last_modified.strftime("%a, %d %b %Y")
            p = {"subject": subject,
                 "content": content,
                 "created": created,
                 "last_modified": last_modified}
            blog_list.append(p)
        j = json.dumps(blog_list)
        self.write(j)


class NewPost(BaseHandler):

    def render_front(self, subject="", content="", error=""):
        self.render("newpost.html",
                    subject=subject,
                    content=content,
                    error=error)

    def get(self):
        if self.user:
            self.render_front()
        else:
            self.redirect("/blog/login")

    def post(self):
        if not self.user:
            self.redirect('/blog')

        subject = self.request.get("subject")
        content = self.request.get("content")

        if subject and content:
            b = Blog(subject=subject, content=content)
            b.put()
            b_key = b.put()  # Key('BlogPost', id)

            top_blogs(True)
            self.redirect("/blog/%d" % b_key.id())
        else:
            error = "You need both a subject and content!"
            self.render_front(subject, content, error)


class Permalink(BaseHandler):

    def get(self, blog_id):
        blogs = top_blogs()[0]
        s = blogs[0]
        start = top_blogs()[1]
        end = datetime.now()
        diff = end - start
        time_passed = int(round(diff.total_seconds()))
        self.render("permalink.html", blog=s, time_passed=time_passed)


class PermalinkJSON(BaseHandler):

    def get(self, blog_id):
        self.response.headers['Content-Type'] = 'application/json'

        s = Blog.get_by_id(int(blog_id))

        subject = s.subject
        content = s.content
        created = s.created.strftime("%a, %d %b %Y")
        last_modified = s.last_modified.strftime("%a, %d %b %Y")

        p = {"subject": subject,
             "content": content,
             "created": created,
             "last_modified": last_modified}
        j = json.dumps(p)
        self.write(j)


application = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/birthday/?', Birthday),
    ('/thanks/?', Thanks),
    ('/rot13/?', Rot13),
    ('/blog/signup/?', SignUp),
    ('/blog/login/?', Login),
    ('/blog/logout/?', Logout),
    ('/blog/welcome/?', Welcome),
    ('/blog/?', BlogFront),
    ('/blog/.json', BlogFrontJSON),
    ('/blog/newpost/?', NewPost),
    ('/blog/(\d+)/?', Permalink),
    ('/blog/(\d+).json', PermalinkJSON),
    ('/blog/flush/?', FlushCache),
], debug=True)