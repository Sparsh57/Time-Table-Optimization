const express = require('express');
const app = express();
app.set('view engine', 'ejs');

const session = require('express-session')
const passport = require('passport')
const GoogleStrategy = require( 'passport-google-oauth2' ).Strategy;

app.use(express.static(__dirname + '/views/'));
const path = require('path');
require("dotenv").config()



//Middleware
app.use(session({
  secret: "secret",
  resave: false ,
  saveUninitialized: true ,
}))
app.use(passport.initialize()) // init passport on every route call
app.use(passport.session())    //allow passport to use "express-session"
//Get the GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET from Google Developer Console
const GOOGLE_CLIENT_ID = "3184701-tn6finlstvgcgvte2381.apps.googleusercontent.com"
const GOOGLE_CLIENT_SECRET = "XyLuTLHX6Ov_93IP"

authUser = (request, accessToken, refreshToken, profile, done) => {
  return done(null, profile);
}

//Use "GoogleStrategy" as the Authentication Strategy
passport.use(new GoogleStrategy({
  clientID: process.env.CLIENT_ID,
  clientSecret: process.env.CLIENT_SECRET,
  callbackURL: "http://localhost:4000/auth/google/callback",
  passReqToCallback   : true
}, authUser));

passport.serializeUser( (user, done) => { 
  console.log(`\n--------> Serialize User:`)
  console.log(user)
   // The USER object is the "authenticated user" from the done() in authUser function.
   // serializeUser() will attach this user to "req.session.passport.user.{user}", so that it is tied to the session object for each session.  

  done(null, user)
} )
passport.deserializeUser((user, done) => {
  console.log("\n--------- Deserialized User:")
  console.log(user)
  // This is the {user} that was saved in req.session.passport.user.{user} in the serializationUser()
  // deserializeUser will attach this {user} to the "req.user.{user}", so that it can be used anywhere in the App.

  done (null, user)
}) 

checkAuthenticated = (req, res, next) => {
  if (req.isAuthenticated()) { return next() }
  res.redirect("/")
}

app.get('/auth/google',
  passport.authenticate('google', { scope:
      [ 'email', 'profile' ] }
));

app.get('/auth/google/callback',
  passport.authenticate( 'google', {
      successRedirect: '/dashboard',
      failureRedirect: '/'
}));

app.post('/logout', function(req, res, next) {
  req.logout(function(err) {
    if (err) { return next(err); }
    res.redirect('/');
  });
});


app.get('/', (req, res) => {
  console.log("hiii");
  res.render('home')
 });

admin = ["aarav_akali.sias22@krea.ac.in"];
profs = [];

app.get('/dashboard',checkAuthenticated, (req, res) => {
  console.log(req.user.email);
  if(admin.includes(req.user.email)){
    console.log("fetching admin dashboard");
    res.render("admin_dashboard", {name: req.user.email});
  }
  else{
    console.log("user not an admin");
  }
});

app.get('/timetable',checkAuthenticated, (req, res) => {
  console.log("enter timetable");
  var data = {
    Moday:["08:30 to 10:30", "10:30 to 12:30", "14:30 to 16:30"],
    Tuedday:["08:30 to 10:30", "10:30 to 12:30", "14:30 to 16:30"]
  }
  for(const key in obj){
    console.log("key {key}");
    for(const item in data.key){
      console.log(item);
    }
  }
  
  res.render("test.ejs", {name: req.user.email});

});

//TODO
app.post('/send_admin_data', (req, res, next) => {
  const form = formidable({});

  form.parse(req, (err, fields, files) => {
    if (err) {
      next(err);
      return;
    }
    res.json({ fields, files });
  });
});
app.listen(4000, () => console.log('Server Started'))