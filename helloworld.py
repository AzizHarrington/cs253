import os
import webapp2
import jinja2

from google.appengine.ext import db

import funcs

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = False)

def escape(somestring):
	return funcs.escape_html(somestring)


def render_str(template, **params):
	t = jinja_env.get_template(template)
	return t.render(params)


class BaseHandler(webapp2.RequestHandler):
	def render(self, template, **kw):
		self.response.out.write(render_str(template, **kw))

	def write(self, *a, **kw):
		self.response.out.write(*a, **kw)


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
			self.render("birthday.html", error = "That doesn't look valid to me, friend.",
							month = escape(user_month), day = escape(user_day), year = escape(user_year))
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
		self.render('rot13.html', text = escape(rot13))


class User(db.Model):
	username = db.StringProperty(required = True)
	password = db.StringProperty(required = True)
	salt = db.StringProperty(required = True)
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

		params = dict(username = username, email = email)

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
			u = User(username=username, password=salted_password[0], salt=salted_password[1], email=email)
			u.put()
			u_id = u.put().id()

			self.response.headers.add_header('Set-Cookie', 'user_id=%s|%s; Path=/' % (u_id, salted_password[0]))
			self.redirect('/welcome')



			


class Welcome(BaseHandler):
	def get(self):
		user_id_cookie = self.request.cookies.get('user_id').split('|')
		user_id = user_id_cookie[0]
		hashbrowns = user_id_cookie[1]

		u = User.get_by_id(int(user_id))

		if u:
			if u.password == hashbrowns:
				self.write("Welcome, %s!" % u.username)
		else:
			self.redirect('/signup')


class Blog(db.Model):
	subject = db.StringProperty(required = True)
	content = db.TextProperty(required = True)
	created = db.DateTimeProperty(auto_now_add = True)
	last_modified = db.DateTimeProperty(auto_now = True)


class BlogFront(BaseHandler):
	def get(self):
		blogs = db.GqlQuery("SELECT	 * 	FROM Blog ORDER BY created DESC")
		self.render("blogfront.html", blogs=blogs)


class NewPost(BaseHandler):
	def render_front(self, subject="", content="", error=""):
		self.render("newpost.html", subject=subject, content=content, error=error)

	def get(self):
		self.render_front()

	def post(self):
		subject = self.request.get("subject")
		content = self.request.get("content")

		if subject and content:
			b = Blog(subject=subject, content=content)
			b.put()
			b_key = b.put() # Key('BlogPost', id)

			self.redirect("/blog/%d" % b_key.id())
		else:
			error = "You need both a subject and content!"
			self.render_front(subject, content, error)

class Permalink(BaseHandler):
	def get(self, blog_id):
		s = Blog.get_by_id(int(blog_id))
		self.render("blogfront.html", blogs=[s])



application = webapp2.WSGIApplication([
	('/', MainPage),
	('/birthday', Birthday),
	('/thanks', Thanks),
	('/rot13', Rot13),
	('/signup', SignUp),
	('/welcome', Welcome),
	('/blog', BlogFront),
	('/blog/newpost', NewPost),
	('/blog/(\d+)', Permalink)
], debug=True)