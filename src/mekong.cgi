#!/usr/bin/perl -w
# Mohammad Ghasembeigi
# COMP2041 assignment 2 - mekong.com.au

use CGI qw/:all/;

#use local perl5 module directory
use lib "./modules/perl5";

### Modules ###
use JSON::XS; #module by Marc Lehmann
use Digest::MD5 qw(md5_hex); #core function, by Gisle Aas, Neil Winton, RSA Data Security, Inc.

#debugging variables
$debug = 0;
$| = 1;

### Eviroment check ###
if (!@ARGV) {
	# run as a CGI script
	cgi_main();
} else {
	# for debugging purposes run from the command line
	console_main();
}
exit 0;

# Main website flow control subroutine
sub cgi_main {
	print page_header(); #print HTML header
	
	set_global_variables();
	read_books($books_file);
	
	#create required directories if they don't exist
	-d $_ or mkdir $_ foreach qw/users baskets orders lostpass auth/;
	
	
	#create orders NEXT_ORDER_NUMBER file if it does not exist and set to 0
	if (! -e "$orders_dir/NEXT_ORDER_NUMBER" || -z "$orders_dir/NEXT_ORDER_NUMBER") {
		open(FILE, '>', "$orders_dir/NEXT_ORDER_NUMBER");
		print FILE "0";
		close(FILE);
	}
	
	my $login = param('username');
	my $search_terms = param('search_terms');
	my $action = param('action');
		
	#if an action is defined, a specific page is produced
	if (defined $action) { 
		if ($action eq "Create New Account") {	#user wants to make a new account
			print new_account();
		} elsif ($action eq "Create Account"){ #details submitted
			my $username = param('username');
			my $password = param('password');
			my $name = param('name');
			my $street = param('street');
			my $city = param('city');
			my $state = param('state');
			my $postcode = param('postcode');
			my $email = param('email');
			
			my $errors =  create_account_check($username, $password, $name, $street, $city, $state, $postcode, $email);
			
			if ($errors ne "") {	#errors were encountered
				print new_account($errors, $username, $name, $street, $city, $state, $postcode, $email);
			} else { #create user auth key
				create_auth_key($username, $password, $name, $street, $city, $state, $postcode, $email);
				print login_form("Check your email for authorization link to activate your account.");
			}	
		} elsif ($action eq "authorize") { #active account if possible
			my $result = process_auth_key();
			
			if ($result ne "") { #errors found
				print login_form($result);
			} else { #successful
				redirect_account(); #redirect with message to homepage
			}
		} elsif ($action eq "Forgot Password?") {
			forgot_pass();
		} elsif ($action eq "Request Recovery Email") {
			$username = param('username');
			my $result = create_forgot_pass($username);
			
			if ($result ne "") { #errors found
				forgot_pass($result);
			} else { #succesful
				print login_form("Check your email for authorization link to recover your account.");
			}
		} elsif ($action eq "recover") {
			my $result = process_forgot_pass();
			
			if ($result ne "") { #errors found
				print login_form($result);
			} else { #successful
				forgot_pass_2();
			}
		} elsif ($action eq "Update Password") {
			my $result = process_forgot_pass_2();
			
			if ($result ne "") { #errors found
				forgot_pass_2($result);
			} else { #successful
				redirect_lost_pass(); #redirect with message
			}
		} elsif ($action eq "Login") {
			my $username = param('username');
			my $password = param('password');
			
			my $authenticate = authenticateLogin($username, $password);
			
			if ($authenticate eq "") { #if it was successful
				user_home_page();
			} else {
				print login_form($authenticate); #print login form with errors
			}
		} elsif ($action eq "home") {
			user_home_page()
		} elsif ($action eq "Search page") { #if search enquired from navbar
			print subheader();
			print "<h1>Search</h1><br />";
			print "<div class=\"center\">";
			#print search form
			print search_form();
			print "</div>";
		} elsif ($action eq "Search") {
			if (defined $search_terms) {
				if ($search_terms eq "") { #if search term empty, return error
					user_home_page("No search query specified.<br/>");
				} else {
					my $result = search_results($search_terms);
					
					if ($result ne "") { #then error has been found, display error
						user_home_page($result);
					}
				}
			}
		} elsif ($action eq "Details") {
			detail_page();
		} elsif ($action eq "Add") {
			my $type = param('addfrom');
			
			if ($type eq "search") { #process and return to search page
				add_process();
				search_results(param('query'), "Item successfully added to basket.");
			} elsif ($type eq "details") {
				add_process();
				detail_page();
			}
		} elsif ($action eq "Check out") {
			checkout_page();
		} elsif ($action eq "Finalize Order") {
			my $result = finalize_order();
			
			print "$result";
			
			if ($result eq "") { #no errors encountered
				view_orders();
			} else { #errors encountered
				checkout_page($result);
			}
			
		} elsif ($action eq "Drop") {
			process_drop();
			
			my $dropfrom = param('dropfrom');
			
			if ($dropfrom eq "Basket") {
				basket_page();
			} elsif ($dropfrom eq "Checkout") {
				checkout_page();
			}
			
		} elsif ($action eq "Basket") { 
			basket_page();
		} elsif ($action eq "View orders") {
			view_orders();
		} elsif ($action eq "Update") { #update basket count
			my $isbn = param('isbn');
			my $count = param('itemcount');
			my $dropfrom = param('dropfrom');
			
			my $result = update_basket($isbn, $count);
			
			if ($result ne "") { #errors found
				if ($dropfrom eq "Basket") {
					basket_page($result);
				} elsif ($dropfrom eq "Checkout") {
					checkout_page($result);
				} elsif ($dropfrom eq "search") {
					search_results(param('query'), $result);
				} else { #go to basket
					detail_page($result);
				}
			} else { #successful
				if ($dropfrom eq "Basket") {
					basket_page("Basket was successfully updated.");
				} elsif ($dropfrom eq "Checkout") {
					checkout_page("Basket was successfully updated.");
				} elsif ($dropfrom eq "search") {
					search_results(param('query'), "Basket was successfully updated.");
				} else { #go to basket
					detail_page("Basket was successfully updated.");
				}
			}
		} elsif ($action eq "Back" || $action eq "Cancel") {
			print login_form();
		}
	} else { #otherwise the user is not logged in, show login form
		print login_form();
	}
	
	#print footer
	print page_footer();
}

#######################
### My Functions ###
#######################

# HTML header (appears on every page)
sub page_header() {
	return <<eof;
Content-Type: text/html

<!DOCTYPE html>
<html lang="en">
<head>
<title>mekong.com.au</title>
<link href="//netdna.bootstrapcdn.com/twitter-bootstrap/2.3.1/css/bootstrap-combined.min.css" rel="stylesheet">
<script src="//netdna.bootstrapcdn.com/twitter-bootstrap/2.3.1/js/bootstrap.min.js"></script>
<link rel="stylesheet" type="text/css" href="style.css">

</head>
<body>
<p>
<div class="container">
eof
}

# HTML footer (appears on every page)
sub page_footer() {
	my $debugging_info = debugging_info();
	
	return <<eof;
	<span class="center" id="copyright">
	<hr />
	Copyright &copy; 2013. Mekong Limited. All Rights Reserved.
	</span>
	$debugging_info
	</div>
<body>
</html>
eof
}


# Print out information for debugging purposes
sub debugging_info() {
	my $params = "";
	foreach $p (param()) {
		$params .= "param($p)=".param($p)."\n"
	}

	return <<eof;
<hr>
<h4>Debugging information - parameter values supplied to $0</h4>
<pre>
$params
</pre>
<hr>
eof
}

#uses sendmail to send HTML type email
#accepts following args: to, username, subject, heading, body
sub send_mail {
	my ($username, $to, $subject, $heading, $body) = @_;
	
	eval {
		open my $sendmail, "| /usr/sbin/sendmail -oi -oeq -t" or die $!;
		print $sendmail <<EOF;
to: $to
from: admin\@mekong.com.au
subject: $subject
Content-Type: text/html
<div style="margin: 0 auto; width:70%; display:block">
<img src="$script_path/images/login.png" width="75%" />
<h2>$heading</h2>
<p>$body</p>
</div>
EOF
	close $sendmail or die "Error closing sendmail: $!";
	};
}

#print logo
sub logo {
	return <<eof;
	<div class = "logo">
	<img src="images/login.png" width="407px" heigth="349px" />
	</div>
eof
}

#print logo
sub smalllogo {
	return <<eof;
	<div class="smalllogo">
	<img src="images/site-name.png" width="286px" heigth="95px" />
	</div>
eof
}

#print subheader for logged in users
sub subheader {
	my $username = param('username');
	
	return <<eof;
	<div id="subheader">
	<!-- Form for actions -->
	<form id="actionform" method="post">
	<input id="actionid" type="hidden" name="action" value="home"></input>
	<input type="hidden" name="username" maxlength="15" value="$username">
	</form>
	
	<img src="images/site-name.png" width="286px" heigth="95px" />
	<span id="navbar">
	<ul>
	<li><a href="#" onclick="document.getElementById('actionid').value = 'home';document.getElementById('actionform').submit();">Home</a></li>
	<li><a href="#" onclick="document.getElementById('actionid').value = 'Search page';document.getElementById('actionform').submit();">Search</a></li>
<li><a href="#" onclick="document.getElementById('actionid').value = 'Basket';document.getElementById('actionform').submit();">Basket</a></li>
	<li><a href="#" onclick="document.getElementById('actionid').value = 'Check out';document.getElementById('actionform').submit();">Checkout</a></li>
	<li><a href="#" onclick="document.getElementById('actionid').value = 'View orders';document.getElementById('actionform').submit();">View Orders</a></li>
	<li style="margin-left: 60px;">Logged in as: <strong>$username</strong></li>
	<li><a href="">Logout</a></li>
	</ul>
	</span>
	</div>
	<hr id="headerline" />
eof
}

#homepage users see upong loging in
sub user_home_page {
	my $username = param('username');
	my $error = $_[0];
	
	print subheader();
	
	print "<h1>Welcome, $username!</h1><br />";
	print "<div class=\"center\" id=\"user_home_page\">"; #wrap in div
	
	#print errors if they exist
	if (defined $error && $error ne "") {
		print "<span class=\"error\">", $error, "</span>";
	}
	
	#print their basket
	basket_table();
	
	print <<eof;
	<br />
	<form method="post">
	<input class="btn" type="submit" name="action" value="Check out">
	<input class="btn" type="submit" name="action" value="View orders">
	<input type="hidden" name="username" maxlength="15" value="$username">
	</form>
	<br />
eof
	
	#print search form
	print search_form();
	
	#print other content for user homepage
	print "</div>";
}

#Returns empty error string if user is properly authenticated
#Returns errors otherwise
sub authenticateLogin() {
	my($username, $password) = @_;
	
	if (!defined $username  || !defined $password || $username eq "" || $password eq "") {
		return "Username and password are required fields.<br>";
	}
	
	#check that user exists
	if (! -r "$users_dir/$username") { #if user file does not exist
		return "Unknown username entered.<br>"
	}
	
	#open file for reading if possible
	if (!open(USER, "<$users_dir/$username")) {
		return "Can not read user file from database.<br>"
	}
	
	my $userInfoString = <USER>;
	my @userComponents = split('\|', $userInfoString);
	
	close(USER);
	
	#hash provided password
	$password = md5hash($password);
	
	#check that username (verify stored username) and passwords match
	if ($username ne $userComponents[0] || $password ne $userComponents[1]) {
		return "Incorrect password provided.<br>";
	}

	return ""; #no 
}

sub new_account {
	my ($errors, $username, $name, $street, $city, $state, $postcode, $email) = @_;
	
	print logo();
	print "<h1>Create new account</h1>";
	
	#print errors if they exist
	if (defined $errors && $errors ne "") {
		print "<span class=\"error\">", $errors, "</span>";
	}
	
	foreach $var ($username, $name, $street, $city, $state, $postcode, $email) {
		if (!defined $var) {
			$var = "";
		}
	}
	
	return <<eof;
	<form method="post">
	<input type="hidden" name="screen" value="new_account"><p /><p /><table align="center"><caption><font color=red></font></caption>
	<tr><td>Username:</td> <td><input type="text" name="username"  width="10" maxlength="15" value="$username"/></td></tr>
	<tr><td>Password:</td> <td><input type="password" name="password"  width="10" maxlength="15"/></td></tr>
	<tr><td>Full Name:</td> <td><input type="text" name="name"  width="50" value="$name"/></td></tr>
	<tr><td>Street:</td> <td><input type="text" name="street"  width="50" value="$street" /></td></tr>
	<tr><td>City/Suburb:</td> <td><input type="text" name="city"  width="25" value="$city"/></td></tr>
	<tr><td>State:</td> <td>
	<select name="state" id ="stateselect">
	  <option value=""></option>
	  <option value="ACT">Australian Capital Territory</option>
	  <option value="NSW">New South Wales</option>
	  <option value="NT">Northern Territory</option>
	  <option value="QLD">Queensland</option>
	  <option value="SA">South Australia</option>
	  <option value="TAS">Tasmania</option>
	  <option value="VIC">Victoria</option>
	  <option value="WA">Western Australia  </option>
	</select>
	<script>document.getElementById('stateselect').value = '$state';</script>
	<tr><td>Postcode:</td> <td><input type="text" name="postcode"  width="25" maxlength="4" value="$postcode"/></td></tr>
	<tr><td>Email Address:</td> <td><input type="text" name="email"  width="35" value="$email" /></td></tr>
	<tr><td></td><td align="center" colspan="1">
	<input class="btn" type="submit" name="action" value="Create Account"><br /><br />
	<input class="btn" type="submit" name="action" value="Back">
	</td></tr></table>
	</form></div>
	
eof
}

#creates random auth key and stores it
sub create_auth_key {
	my ($username, $password, $name, $street, $city, $state, $postcode, $email) = @_;
	

	#generate random auth key
	my @chars = ("A".."Z", "a".."z");
	my $key;
	$key .= $chars[rand @chars] for 1..15;
	
	#hash encrypt password
	$password = md5hash($password);
	
	
	open(AUTH, ">$auth_dir/$username");
	print AUTH "$key|$username|$password|$name|$street|$city|$state|$postcode|$email"; 
	close(AUTH);

	#email user auth key
	my $subject = "Activate your account | Mekong.com.au";
	my $heading = "Hey $username!";
	my $body = "You can activate your Mekong.com.au account by clicking on the link below:<br/>
				<a href=\"$script_url?action=authorize&username=$username&authorization_key=$key\">$script_url?action=authorize&username=$username&authorization_key=$key</a>";
	
	send_mail($username, $email, $subject, $heading, $body);
}

#checks if auth key is correct or if it is incorrent
sub process_auth_key {
	my $provided_auth = param('authorization_key');
	my $username = param('username');
	my $errors = "";
	
	if (! open(AUTH, "<$auth_dir/$username")) {#read in the info key for user
		$errors .= "Username does not exist or has already been activated.";
		return $errors;
	}	
	my $auth = <AUTH>;
	chomp $auth;
	close(AUTH);

	my @components = split('\|', $auth);
	
	if (! defined $username) {
		$errors .= "Missing username parameter.";
		return $errors;
	}
	
	if ($provided_auth ne $components[0]) {
		$errors .= "Incorrect authorization key provided";
		return $errors;
	}
	
	#if no errors detected
	$auth =~ s/^[^\|]*\|//; #remove auth key field
	unlink "$auth_dir/$username"; #remove auth file
	
	open(USER, ">$users_dir/$username");
	#note, | is forbidden char in fields (it is sanitized into html)
	print USER "$auth"; 
	close(USER);
	
	return $errors;
}

#redirects user to homepage after account activation
sub redirect_account {
	my $username = param('username');
	print smalllogo();
	
	print <<eof
	<div class="center">
	<h1>Hey $username! Welcome to mekong.com.au!</h1>
	<br />
	<p>Redirecting to homepage in 5 seconds...</p>
	<script type="text/JavaScript">
	<!--
	setTimeout("window.location=\'$script_url\'" ,5000);
	-->
	</script>
	</div>
eof
}

#checks account information for errors, 
#if no errors found, returns empty string, else returns errors as string
sub create_account_check {
	my ($username, $password, $name, $street, $city, $state, $postcode, $email) = @_;
	my $errors = "";
	my $fields = 0;
	my $fieldtext = "Please provide input for the following required fields:<br>";
	
	
	#username check
	if ($username eq "") {
		$fields = 1;
		$fieldtext .= "- Username<br>";
	} else {
		#user exists check
		if (-r "$users_dir/$username" || -r "$auth_dir/$username") {
			$errors .=  "Provided username already exists.<br>";
		}
		
		#permission check
		if (!open(USER, ">$users_dir/$username")) {
			$errors .= "Can not read user file from database.<br>";
		}
		
		unlink ("$users_dir/$username");
		close(USER);
		
		if ($username =~ /[^A-Za-z0-9]/) {
			$errors .=  "Invalid characters in username. Only A-Za-z0-9 permitted.<br>";
		}
		if (length($username) < 4 || length($username) > 15 ) {
			$errors .=  "Username must be between 4 and 15 characters long.<br>";
		}
	}
	#password check
	if ($password eq "") {
		$fields = 1;
		$fieldtext .= "- Password<br>";
	} else {
		if ($password =~ /[^A-Za-z0-9@#$!%^&*]/) {
			$errors .=  "Invalid characters in password. Only A-Za-z0-9@#$!%^&* permitted.<br>";
		}
		if (length($password) < 6 || length($password) > 15) {
			$errors .=  "Password must be between 6 and 15 characters long.<br>";
		}
	}
	
	#name check
	if ($name eq "") {
		$fields = 1;
		$fieldtext .= "- Full Name<br>";
	} else {
		if ($name =~ /[^A-Za-z- ]/) {
			$errors .=  "Invalid characters in full name. Only A-Za-z, dashes and spaces permitted.<br>";
		}
	}
	
	#street check - allow any input
	if ($street eq "") {
		$fields = 1;
		$fieldtext .= "- Street<br>";
	} else {
		if ($street =~ /[|]/) {
			$errors .=  "Invalid character in street. '|' character is not permitted.<br>";
		}
	}
	
	#city check - allow any input
	if ($city eq "") {
		$fields = 1;
		$fieldtext .= "- City/Suburb<br>";
	} else {
		if ($city =~ /[|]/) {
			$errors .=  "Invalid character in city/suburb. '|' character is not permitted.<br>";
		}
	}
	
	#state check - allow any input
	if ($state eq "") {
		$fields = 1;
		$fieldtext .= "- State<br>";
	} else {
		if ($state !~ /^(ACT|NSW|SA|QLD|TAS|VIC|WA|NT)$/) { #if not a valid state
			$errors .= "Unknown state selected.<br>";
		}
	}
	
	#postcode check 
	if ($postcode eq "") {
		$fields = 1;
		$fieldtext .= "- Postcode<br>";
	} else {
		if ($postcode !~ /[0-9]{4}/) { #require 4 numbers
			$errors .=  "Invalid postcode entered.<br>";
		}
	}
	
	#email check
	if ($email eq "") {
		$fields = 1;
		$fieldtext .= "- Email Address<br>";
	} else {
		if ($email !~ /^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$/) { #invalid email entered
			$errors .=  "Invalid email entered.<br>";
		}
		if ($email =~ /[|]/) {
			$errors .=  "Invalid character in email. '|' character is not permitted.<br>";
		}
	}
	
	#if missing fields detected, append those errors too
	if ($fields) {
		$errors .= "<br>" . $fieldtext;
	}
	
	return $errors;
}

# Login Form with authentication
sub login_form {

	print logo();
	
	my $error = $_[0];
	
	#print errors if they exist
	if (defined $error && $error ne "") {
		print "<span class=\"error\">", $error, "</span>";
	}
	
	return <<eof;
	<div id = "login">
	
	<p>
	<form method="post">
		Username: <input type="text" name="username" width="10" maxlength="15"></input><br />
		Password: <input type="password" name="password" width="10" maxlength="15"></input><br /><br />
		<input class="btn" type="submit" name="action" value="Login">
		<input class="btn" type="submit" name="action" value="Create New Account"><br /><br />
		<input class="btn" type="submit" name="action" value="Forgot Password?">
	</form>
	<p>
	</div>
eof
}

# simple search form
sub search_form {
	my $username = param('username');
	
	return <<eof;
	<div id = "search">
	<p>
	<form method ="post">
		Search for items:<br />
		<input type="text" name="search_terms" style="width: 320px;" size=60></input><br/>
		<input class="btn" type="submit" name="search_button" value="Search">
		<input type="hidden" name="username" maxlength="15" value="$username">
		<input type="hidden" name="action" value="Search"><br />
	</form>
	</p>
	</div>
eof
}

# Search json  file (ie, item database) for files and to find matching items
sub search_results {
	my ($search_terms) = $_[0];
	my $displayerrors = $_[1] if defined $_[1];
	
	my @matching_isbns = search_books($search_terms);
	
	my $username = param('username');

	my $json = "";
	my $items;
	my $errors = "";
	
	print subheader();
	
	if ($#matching_isbns+1 == 0) { #if no matching items
		print <<eof;
		<h2>Search results for: $search_terms</h2><br />
		<p>Sorry, there were no matching results for your query.</p>
eof
	} elsif (!open(ITEM, '<', "$books_file")) { #see if we can open json file
		#error cant access items database
		$errors = "Cannot access items database. Please contact administrator.<br />";
		return $errors;
	} else {	#else file can be opened
		print <<eof;
		<h2>Search results for: $search_terms</h2>
eof
		#print errors if they exist
		if (defined $displayerrors && $displayerrors ne "") {
			print "<span class=\"error\">", $displayerrors, "</span>";
		}

		print <<eof;
		<div id="searchtable"><br />
eof
	
		while (<ITEM>) {	#read in the input
			$json .= $_;
		}

		if ($json ne "") { #if json file contains information
			$items = decode_json($json); 	#decode it

			print <<eof;
			<table bgcolor="white" border="1" align="center"><caption></caption>
			<tbody>
eof
			foreach $isbn (@matching_isbns) {	#for each isbn, gather required information about the book
				#create variables that are required
				my ($title, $authorstring, $price, $smallpic, $largepic, $productdescription,
							$binding, $ean, $edition, $catalog, $numpages, $publication_date, $publisher,
							$releasedate, $salesrank, $year);
				
				#initilise these variables
				$title = $authorstring = $price = $smallpic = $largepic = $productdescription = $binding = $ean = $edition = $catalog = $numpages = $publication_date = $publisher = $releasedate = $salesrank = $year = "";
				
				#collect neccary variables
				$title = sanitizeString( $items->{$isbn}{'title'} ) if defined $items->{$isbn}{'title'};

				my @authors = @{ $items->{$isbn}{'authors'} }; #array of authors, need to dereference
				$authorstring = join(', ', @authors);
				$authorstring = sanitizeString($authorstring);

				$price = sanitizeString( $items->{$isbn}{'price'} ) if defined $items->{$isbn}{'price'};
				$smallpic = sanitizeString( $items->{$isbn}{'smallimageurl'} ) if defined $items->{$isbn}{'smallimageurl'};

				my $getcount = get_item_count($isbn);
				
				print <<eof;
				<tr><td><img class="search_small_image" src="$smallpic"></td>
				<td><i>$title</i><br />$authorstring<br /><br /><strong>ISBN: </strong>$isbn<br /></td> 
				<td align="right"><tt>$price</tt></td> 
				<td>
				<form style="margin-bottom:0;" method="post">
eof
	
				if ($getcount == 0) { #item not found, show 1
					print "<input type=\"text\" name=\"itemcount\" value=\"1\" class=\"itemcount\"></input>";
				} else { #display true count
					print "<input type=\"text\" name=\"itemcount\" value=\"$getcount\" class=\"itemcount\"></input>";
				}
				
				print <<eof;
				</td>
				<td>
				
				<input type="hidden" name="username" maxlength="15" value="$username">
				<input type="hidden" name="isbn" value="$isbn">
				<input type="hidden" name="addfrom" value="search">
				<input type="hidden" name="query" value="$search_terms">
				<input type="hidden" name="dropfrom" value="search">
eof

				if ($getcount == 0) { #item not found, show add
					print "<input class=\"btn widebtn\" type=\"submit\" name=\"action\" value=\"Add\"><br>";
				} else { #display update
					print "<input class=\"btn widebtn\" type=\"submit\" name=\"action\" value=\"Update\"><br>";
				}
				
				print <<eof;			
				<input class="btn widebtn" type="submit" name="action" value="Details"><br>
				</form>
				</td></tr>
eof
			}
			
			print <<eof;
			</tbody></table></div>
eof
		}
		close(ITEM);
	}
	
	return $errors;
}

# return books matching search string
sub search_books {
	my ($search_string) = @_;
	$search_string =~ s/\s*$//;
	$search_string =~ s/^\s*//;
	return search_books1(split /\s+/, $search_string);
}

# return books matching search terms
sub search_books1 {
	my (@search_terms) = @_;
	our %book_details;
	print STDERR "search_books1(@search_terms)\n" if $debug;
	my @unknown_fields = ();
	foreach $search_term (@search_terms) {
		push @unknown_fields, "'$1'" if $search_term =~ /([^:]+):/ && !$attribute_names{$1};
	}
	printf STDERR "$0: warning unknown field%s: @unknown_fields\n", (@unknown_fields > 1 ? 's' : '') if @unknown_fields;
	my @matches = ();
	BOOK: foreach $isbn (sort keys %book_details) {
		my $n_matches = 0;
		if (!$book_details{$isbn}{'=default_search='}) {
			$book_details{$isbn}{'=default_search='} = ($book_details{$isbn}{title} || '')."\n".($book_details{$isbn}{authors} || '');
			print STDERR "$isbn default_search -> '".$book_details{$isbn}{'=default_search='}."'\n" if $debug;
		}
		print STDERR "search_terms=@search_terms\n" if $debug > 1;
		foreach $search_term (@search_terms) {
			my $search_type = "=default_search=";
			my $term = $search_term;
			if ($search_term =~ /([^:]+):(.*)/) {
				$search_type = $1;
				$term = $2;
			}
			print STDERR "term=$term\n" if $debug > 1;
			while ($term =~ s/<([^">]*)"[^"]*"([^>]*)>/<$1 $2>/g) {}
			$term =~ s/<[^>]+>/ /g;
			next if $term !~ /\w/;
			$term =~ s/^\W+//g;
			$term =~ s/\W+$//g;
			$term =~ s/[^\w\n]+/\\b +\\b/g;
			$term =~ s/^/\\b/g;
			$term =~ s/$/\\b/g;
			next BOOK if !defined $book_details{$isbn}{$search_type};
			print STDERR "search_type=$search_type term=$term book=$book_details{$isbn}{$search_type}\n" if $debug;
			my $match;
			eval {
				my $field = $book_details{$isbn}{$search_type};
				# remove text that looks like HTML tags (not perfect)
				while ($field =~ s/<([^">]*)"[^"]*"([^>]*)>/<$1 $2>/g) {}
				$field =~ s/<[^>]+>/ /g;
				$field =~ s/[^\w\n]+/ /g;
				$match = $field !~ /$term/i;
			};
			if ($@) {
				$last_error = $@;
				$last_error =~ s/;.*//;
				return (); 
			}
			next BOOK if $match;
			$n_matches++;
		}
		push @matches, $isbn if $n_matches > 0;
	}
	
	sub bySalesRank {
		my $max_sales_rank = 100000000;
		my $s1 = $book_details{$a}{SalesRank} || $max_sales_rank;
		my $s2 = $book_details{$b}{SalesRank} || $max_sales_rank;
		return $a cmp $b if $s1 == $s2;
		return $s1 <=> $s2;
	}
	
	return sort bySalesRank @matches;
}

#display detail page for item based on isbn
sub detail_page {
	my $username = param('username');
	my $bookinfo = getBookInfo();
	my $itemcount = param('itemcount');
	
	my $errors = $_[0] if defined $_[0];
	
	my $getcount = get_item_count($bookinfo->{'isbn'});

	print subheader();

	print <<eof;
	<h2>$bookinfo->{'title'}</h2>
	<p>$bookinfo->{'productdescriptionHTML'}</p>

	<table align="center"><tr><td><img src="$bookinfo->{'largepic'}"></td>
	</table><br />
	<table align="center">
	<tr><td><b>Authors</b></td> <td>$bookinfo->{'authors'}</td></tr>
	<tr><td><b>Binding</b></td> <td>$bookinfo->{'binding'}</td></tr>
	<tr><td><b>Catalog</b></td> <td>$bookinfo->{'catalog'}</td></tr>
	<tr><td><b>EAN</b></td> <td>$bookinfo->{'ean'}</td></tr>
	<tr><td><b>Edition</b></td> <td>$bookinfo->{'edition'}</td></tr>
	<tr><td><b>ISBN</b></td> <td>$bookinfo->{'isbn'}</td></tr>
	<tr><td><b>Number of Pages</b></td> <td>$bookinfo->{'numpages'}</td></tr>
	<tr><td><b>Price (\$AUD)</b></td> <td>$bookinfo->{'price'}</td></tr>
	<tr><td><b>Publication Date</b></td> <td>$bookinfo->{'publication_date'}</td></tr>
	<tr><td><b>Publisher</b></td> <td>$bookinfo->{'publisher'}</td></tr>
	<tr><td><b>Release Date</b></td> <td>$bookinfo->{'releasedate'}</td></tr>
	<tr><td><b>Sales Rank</b></td> <td>$bookinfo->{'salesrank'}</td></tr>
	<tr><td><b>Title</b></td> <td>$bookinfo->{'title'}</td></tr>
	<tr><td><b>year</b></td> <td>$bookinfo->{'year'}</td></tr>
	</table>
	<br /><br />
	<div class="center">
	<form method="post">
	<input type="hidden" name="isbn" value="$bookinfo->{'isbn'}">

	<input type="hidden" name="username" maxlength="15" value="$username">
	
	<input type="hidden" name="addfrom" value="details">
	
eof

	#print errors if they exist
	if (defined $errors && $errors ne "") {
		print "<span class=\"error\">", $errors, "</span>";
	}

	if ($getcount == 0) { #item not found, show 1
		print "<p>Quantity: <input type=\"text\" name=\"itemcount\" value=\"1\" class=\"itemcount\"></input>";
	} else { #display true count
		print "<p>Quantity: <input type=\"text\" name=\"itemcount\" value=\"$getcount\" class=\"itemcount\"></input>";
	}
	
	print <<eof;
	</p><br />
	<input type="hidden" name="dropfrom" value="details">
eof
	if ($getcount == 0) { #item not found, show add
		print "<input class=\"btn\" type=\"submit\" name=\"action\" value=\"Add\"><br>";
	} else { #display update
		print "<input class=\"btn\" type=\"submit\" name=\"action\" value=\"Update\"><br>";
	}
	
	print <<eof;
	<br>
	<input class="btn" type="submit" name="action" value="Basket">
	<input class="btn" type="submit" name="action" value="Check out">
	</form>
	</div>
eof
}

#process file and add it to user basket
sub add_process {
	my $username = param('username');
	my $itemcount = param('itemcount');
	my $isbn = param('isbn');
	
	my $result = update_basket($isbn, $itemcount);
	
	if ($result eq "") { #no errors encountered, item was in cart and has been updated
		return;
	} else { #item not in cart, add manually
		my $bookinfo = getBookInfo();
		
		open(BASKET, ">>$baskets_dir/$username"); #open in append mode
		#note, | is forbidden char in fields
		print BASKET "$bookinfo->{'isbn'}|$bookinfo->{'title'}|$bookinfo->{'authors'}|$bookinfo->{'price'}|$bookinfo->{'smallpic'}|$bookinfo->{'largepic'}|$bookinfo->{'productdescription'}|$bookinfo->{'ean'}|$bookinfo->{'edition'}|$bookinfo->{'catalog'}|$bookinfo->{'numpages'}|$bookinfo->{'publication_date'}|$bookinfo->{'publisher'}|$bookinfo->{'releasedate'}|$bookinfo->{'salesrank'}|$bookinfo->{'year'}|$itemcount\n";
		close(BASKET);
	}
}

#based on isbn parameter, returns hash filled with information about book
sub getBookInfo {
	my $username = param('username');
	my $isbn = sanitizeString( param('isbn'));
	
	my $items;
	my $json = "";
	
	open(ITEM, '<', "$books_file");
	
	while (<ITEM>) {	#read in the input
		$json .= $_;
	}
	close(ITEM);
	
	if ($json ne "") { #if json file contains information
		$items = decode_json($json); 	#decode it
	} 
	
	#create variables that are required
	my ($title, $authorstring, $price, $smallpic, $largepic, $productdescription, $productdescriptionHTML,
			$binding, $ean, $edition, $catalog, $numpages, $publication_date, $publisher,
			$releasedate, $salesrank, $year);

	#initilise these variables
	$title = $authorstring = $price = $smallpic = $largepic = $productdescription = $productdescriptionHTML = $binding = $ean = $edition = $catalog = $numpages = $publication_date = $publisher = $releasedate = $salesrank = $year = "";

	
	#collect neccary variables
	$title = sanitizeString( $items->{$isbn}{'title'} ) if defined $items->{$isbn}{'title'};
	
	my @authors = @{ $items->{$isbn}{'authors'} }; #array of authors, need to dereference
	$authorstring = join(', ', @authors);
	$authorstring = sanitizeString($authorstring);
	
	$price = sanitizeString( $items->{$isbn}{'price'} ) if defined $items->{$isbn}{'price'};
	$smallpic = sanitizeString( $items->{$isbn}{'smallimageurl'} ) if defined $items->{$isbn}{'smallimageurl'};
	$largepic = sanitizeString( $items->{$isbn}{'largeimageurl'} ) if defined $items->{$isbn}{'largeimageurl'};
	
	$productdescriptionHTML = $items->{$isbn}{'productdescription'} if defined $items->{$isbn}{'productdescription'};
	$productdescription = sanitizeString( $items->{$isbn}{'productdescription'} ) if defined $items->{$isbn}{'productdescription'};
	
	$binding = sanitizeString( $items->{$isbn}{'binding'} ) if defined $items->{$isbn}{'binding'};
	$ean = sanitizeString( $items->{$isbn}{'ean'} ) if defined $items->{$isbn}{'ean'};
	$edition = sanitizeString( $items->{$isbn}{'edition'} ) if defined $items->{$isbn}{'edition'};
	$catalog = sanitizeString( $items->{$isbn}{'catalog'} ) if defined $items->{$isbn}{'catalog'};
	$numpages = sanitizeString( $items->{$isbn}{'numpages'} ) if defined $items->{$isbn}{'numpages'};
	$publication_date = sanitizeString( $items->{$isbn}{'publication_date'} ) if defined $items->{$isbn}{'publication_date'};
	$publisher = sanitizeString( $items->{$isbn}{'publisher'} ) if defined $items->{$isbn}{'publisher'};
	$releasedate = sanitizeString( $items->{$isbn}{'releasedate'} ) if defined $items->{$isbn}{'releasedate'} ;
	$salesrank = sanitizeString( $items->{$isbn}{'salesrank'} ) if defined $items->{$isbn}{'salesrank'};
	$year = sanitizeString( $items->{$isbn}{'year'} ) if defined $items->{$isbn}{'year'};
	
	#create book info hash
	my %bookinfo;
	$bookinfo{'isbn'} = $isbn;
	$bookinfo{'title'} = $title;
	$bookinfo{'authors'} = $authorstring;
	$bookinfo{'price'} = $price;
	$bookinfo{'smallpic'} = $smallpic;
	$bookinfo{'largepic'} = $largepic;
	$bookinfo{'productdescription'} = $productdescription;
	$bookinfo{'productdescriptionHTML'} = $productdescriptionHTML;
	$bookinfo{'binding'} = $binding;
	$bookinfo{'ean'} = $ean;
	$bookinfo{'edition'} = $edition;
	$bookinfo{'catalog'} = $catalog;
	$bookinfo{'numpages'} = $numpages;
	$bookinfo{'publication_date'} = $publication_date;
	$bookinfo{'publisher'} = $publisher;
	$bookinfo{'releasedate'} = $releasedate;
	$bookinfo{'salesrank'} = $salesrank;
	$bookinfo{'year'} = $year;
	
	return \%bookinfo;
}

#print standalone basket page 
sub basket_page {
	my $username = param('username');
	
	my $error = $_[0];
	
	print subheader();
	print "<h1>Basket</h1>";
	
	#print errors if they exist
	if (defined $error && $error ne "") {
		print "<span class=\"error\">", $error, "</span>";
	}
	
	basket_table();
	
	print <<eof;
	<br />
	<form method="post" class="center">
	<input class="btn" type="submit" name="action" value="Check out">
	<input class="btn" type="submit" name="action" value="View orders">
	<input type="hidden" name="username" maxlength="15" value="$username">
	</form>
	<br />
eof
}

#print basket table
sub basket_table {
	my $username = param('username');
	my $dropfrom = "Basket";
	$dropfrom = $_[0] if defined $_[0];
	
	#read basket information if possible
	if (! open(BASKET, '<' , "$baskets_dir/$username") || (-z  "$baskets_dir/$username") ) {
		print "<span id =\"basket\">Your Shopping Basket is currently empty.<br /></span>";
		return;
	}

	#print start of table
	print <<eof;
	<table bgcolor="white" border="1" align="center">
	<caption>Your Shopping Basket</caption>
	<tbody>
eof
	
	my $totalprice = 0;
	
	while (<BASKET>) {#for each line
		chomp;
		my @basket = split('\|', $_);
		
		print <<eof;
		<tr>
		<td><img class="search_small_image" src="$basket[4]"></td>
		<td><i>$basket[1]</i><br />$basket[2]<br /><br /><strong>ISBN: </strong>$basket[0]<br /></td>
		<td align="right"><tt>$basket[3]</tt></td>
		<td>
		<input type="text" id="itemcountdisplay" value="$basket[16]" class="itemcount"></input>
		</td>
		<td width="150px">
		<form method="post">
		<input type="hidden" id ="itemcount" name="itemcount" value="$basket[16]">
		<input type="hidden" name="username" maxlength="15" value="$username">
		<input type="hidden" name="isbn" value="$basket[0]">
		<input id="dropfromID" type="hidden" name="dropfrom" value="$dropfrom">
		<input class="btn" style="width:100%;" type="submit" name="action" value="Update"
		onclick="document.getElementById('itemcount').value = 
		document.getElementById('itemcountdisplay').value
		document.getElementById('basketform').submit();">
		<br />
		<input class="btn" style="margin-top: 2px;width:70px" type="submit" name="action" value="Drop">
		<input class="btn" style="width:75px;" type="submit" name="action" value="Details">
		<br>
		</tr>
		</form>
eof

		$basket[3] =~ s/\$//g; #remove price dollar sign
		$totalprice = $totalprice + (scalar($basket[3]) * $basket[16]);
	}
	
	close(BASKET);
	print <<eof;
	<tr><td><b>Total</b></td> <td></td><td></td> <td align="right"><strong>\$$totalprice</strong></td></tr>
	</tbody></table>
eof
}

#update basket based on new count and isbn
#will return error if item not in basket
sub update_basket {
	my $username = param('username');
	my $errors = "";
	my ($isbn, $count) = @_;
	
	#validity checks on count
	if ($count !~ /^\d*$/ || $count < 1) {
		$errors .= "Item count must be a positive integer greater than or equal to 1.";
		return $errors;
	}
	
	#treat as number
	$count = $count + 0;
	
	#read in basket to find count
	if (! open(BASKET, '<' , "$baskets_dir/$username") || (-z  "$baskets_dir/$username") ) {
		$errors .= "Could not access user basket. Please contact administator.";
		return $errors;
	}
	
	my $newbasket = "";
	my $itemfound = 0;
	
	while (my $line = <BASKET>) { #loop through all lines
		if ($line =~ /^$isbn.*/) { #if item found, make item components array
			my @components = split('\|', $line);
			$components[16] = $count; #update count
			$line = join('|', @components);
			$itemfound = 1;
		}
		
		$newbasket .= $line; #write line to basket
	}
	close(BASKET);
	
	if ($itemfound == 0) { #did not find item, return error
		$errors .= "Item not found in user basket, cannot update item count.";
		return $errors;
	} else { #write new basket
		open(BASKET, '>' , "$baskets_dir/$username");
		print BASKET $newbasket;
		close(BASKET);
	}
	
	return $errors;
}

#takes in isbn and returns count
#returns 0 if count not found
sub get_item_count {
	my $isbn = $_[0];
	
	my $username = param('username');
	
	#read in basket to find count
	if (! open(BASKET, '<' , "$baskets_dir/$username") || (-z  "$baskets_dir/$username") ) {
		return 0;
	}
	
	my $count = 0;
	
	while (my $line = <BASKET>) { #loop through all lines
		if ($line =~ /^$isbn.*/) { #if item found, make item components array
			my @components = split('\|', $line);
			$count = $components[16]+0;
		}
	}
	close(BASKET);
	
	return $count;
}

#print checkout page
sub checkout_page() {
	my $username = param('username');
	my $errors = $_[0];
	
	print subheader();
	print "<h1>Checkout</h1>";
	
	basket_table("Checkout"); #call basket with checkout prev page

	#get shipping address of user
	open(USER, "<$users_dir/$username");
	my $userInfoString = <USER>;
	close(USER);
	
	my @userarray = split('\|', $userInfoString);

	#only print elements if basket is not empty
	if (open(BASKET, '<' , "$baskets_dir/$username") && (! -z  "$baskets_dir/$username") ) {
		close(BASKET);
	
	
		#print shipping details
		print <<eof;
		<br />
		<h4>Your shipping address</h4>
		<pre>
		$userarray[2]
		$userarray[3]
		$userarray[4]
		$userarray[5] $userarray[6]
		$userarray[7]
		</pre>
eof
		
		#print payment form
		print <<eof;
		<br />
		<h4>Payment details</h4>
eof

		#print errors if they exist
		if (defined $errors && $errors ne "") {
			print "<span class=\"error\">", $errors, "</span><br />";
		}
		
		print <<eof;
		<form method="post">
		<input type="hidden" name="screen" value="finalize_order">
		<p></p><table align="center"><caption><font color="red"></font></caption>
		<tbody><tr><td>Credit Card Number:</td> <td><input type="text" name="credit_card_number" maxlength="16"></td></tr>
		<tr><td>Expiry date (mm/yy):</td> <td><input type="text" name="expiry_date" maxlength="5"></td></tr>
		<tr><td align="center" colspan="4">
		<input class="btn" type="submit" name="action" value="Finalize Order"><br />
		<input type="hidden" name="username" value="$username">
		</td></tr></tbody></table>

		</form>
eof

	}
	print <<eof;
	<br />
	<form method="post" class="center">
	<input type="hidden" name="username" value="$username">
	<input class="btn" type="submit" name="action" value="Basket">
	<input class="btn" type="submit" name="action" value="View orders">
	</form>
eof
}

#finalize order
#returns empty string if no errors and processes completed successfully
#otherwise returns errors
sub finalize_order {
	my $errors = "";
	my $username = param('username');
	
	my $credit_card_number = param('credit_card_number');
	my $expiry_date = param('expiry_date');
	
	#do error checking
	if ($credit_card_number !~ /^\d{16}$/) {
		$errors .= "Invalid credit card number - must be 16 digits.<br />";
	}
	
	if ($expiry_date !~ /^\d\d\/\d\d$/) {
		$errors .= "Invalid expiry date - must be mm/yy<br />";
	} else {
		#check expiry date
		my ($expirymonth, $expiryyear);
		
		if ($expiry_date =~ /^(\d\d)\/(\d\d)$/) {
			$expirymonth = $1+0;
			$expiryyear = $2+0;
		}
		#use localtime to fetch variables of importance
		my $currentmonth = (localtime)[4] + 1;
		my $currentyear = (localtime)[5] + 1900;
		
		if ($currentyear =~ /^(\d{2})(\d{2})$/) {
			$currentyear = $2;
		}
		
		if ( $expiryyear < $currentyear) { 
			$errors .= "Entered credit card has expired.<br />";
		} elsif ($expiryyear == $currentyear) {
			if ($expirymonth < $currentmonth) {
				$errors .= "Entered credit card has expired.<br />";
			}
		}
		
	}
	
	if ($errors eq "") { #if no errors found, finalise the order
		#read basket information if possible
		if (! open(BASKET, '<' , "$baskets_dir/$username") || (-z  "$baskets_dir/$username") ) {
			$errors .= "Error processing payment. Please contact administrator.<br />";
		} else {
			open(ORDERS, ">>$orders_dir/$username"); #open orders in append mode
			
			#determine order number
			my $ordernumber = 0;
			
			open(ORDERNUMBER, '<' , "$orders_dir/NEXT_ORDER_NUMBER"); #open in read mode
			$ordernumber=<ORDERNUMBER>;
			$ordernumber++;
			close(ORDERNUMBER);
			
			open(ORDERNUMBER, '>' , "$orders_dir/NEXT_ORDER_NUMBER"); #open in write mode
			print ORDERNUMBER "$ordernumber";
			close(ORDERNUMBER);
			
			#determine current time in short form
			$time = time;
			
			#store order header 
			print ORDERS "ORDER_START|$ordernumber|$time|$credit_card_number|$expiry_date\n";
			
			#store each item in order
			while (<BASKET>) { #for each item
				chomp;
				print ORDERS "$_\n"; 
			}
			
			#store order end
			print ORDERS "ORDER_END\n";
			close (ORDERS);
			
			close (BASKET);
			
			#delete users basket file (as all files have just been ordered)
			unlink "$baskets_dir/$username";
			
		}
	}
	
	return $errors;
}

#takes in a string any sanitized input for HTML output
sub sanitizeString {
	my $input = $_[0];
	$input =~ s/\\/&#92;/g;
	$input =~ s/\//&#47;/g;
	$input =~ s/"/&quot;/g;
	$input =~ s/'/&#39;/g;
	$input =~ s/</&lt;/g;
	$input =~ s/>/&gt;/g;
	$input =~ s/\|/&#123;/g;
	return $input;
}

#takes in string and returns MD5 Hash
sub md5hash {
	return md5_hex($_[0]);
}

#view previously placed orders
sub view_orders {
	my $username = param('username');
	
	print subheader();
	print "<h1>View Orders</h1>";
	
	#read order information if possible
	if (! open(ORDERS, '<' , "$orders_dir/$username") || (-z  "$orders_dir/$username") ) {
		print "<span id =\"basket\">You have not placed any orders.<br /></span>";
		return;
	}

	my $totalprice = 0; #variable to hold total price
	
	while (<ORDERS>) {#for each line
		chomp;
		my @line = split('\|', $_);
		
		if ($line[0] eq "ORDER_START") { #print out order details and table start
			#print start of table
			my $time = scalar localtime($line[2]);
			print <<eof;
			<br /><h3>Order #$line[1]</h3>
			<p class="center"><strong>Order placed:</strong> $time<br/><strong>Credit Card Number:</strong> $line[3] (<strong>Expiry</strong> $line[4])</p>
			<br /><table bgcolor="white" border="1" align="center">
			<tbody>
eof
		} elsif ($line[0] eq "ORDER_END") { #print out end of table
			print <<eof;
			<tr><td><b>Total</b></td> <td></td> <td align="right">
			<strong>\$$totalprice</strong></td></tr>
			</tbody></table>
eof
			$totalprice = 0; #reset total price
		} else { #print out item information
			print <<eof;
			<tr><td><img class="search_small_image" src="$line[4]"></td>
			<td><i>$line[1]</i><br />$line[2]<br /><br /><strong>ISBN: </strong>$line[0]<br /></td>
			<td>
			$line[16]
			</td>
			<td align="right"><tt>$line[3]</tt></td>
			<td>
eof

			#calculate the total price
			$line[3] =~ s/\$//g; #remove price dollar sign
			$totalprice = $totalprice + ( scalar($line[3]) * $line[16]);
		}
	}
	close(ORDERS);
	
}

#drop item from basket
sub process_drop {
	my $username = param('username');
	my $isbn = param('isbn');
	
	#read basket information if possible
	if (! open(BASKET, '<' , "$baskets_dir/$username") || (-z  "$baskets_dir/$username") ) {
		return;
	}
	
	my $basket = "";
	
	while (my $line = <BASKET>) { #loop through all lines
		#do not print out item isbn line we want to drop, 
		#note isbn has to be at start so isbns in other item descriptions is fine
		$basket .= $line unless $line =~ /^$isbn.*/;
	}
	close(BASKET);
	
	open(BASKET, '>' , "$baskets_dir/$username");
	print BASKET $basket;
	close(BASKET);
}

#allows user to enter their username so that they can
#be emailed a link to reset their password
sub forgot_pass {
	print logo();
	
	my $errors = $_[0] if defined $_[0];
	
	print "<h1>Forgotten Password</h1>";
	
	#print errors if they exist
	if (defined $errors && $errors ne "") {
		print "<span class=\"error\">", $errors, "</span>";
	}

	print <<eof;
	<form method="post" class="center">
	<table align="center">
	<tr><td>Enter your Username: </td> 
	<td>
	<input type="text" name="username"  width="10" maxlength="15" /></td></tr>
	<tr><td></td>
	<td>
	<input class="btn" type="submit" name="action" value="Request Recovery Email"><br /><br />
	<input class="btn" type="submit" name="action" value="Back"></td></tr>
	</table>
	</form>
eof
}

#makes special forgotten password link and emails user
sub create_forgot_pass {
	my $username = $_[0];
	my $errors = "";
	
	#generate random auth key
	my @chars = ("A".."Z", "a".."z");
	my $key;
	$key .= $chars[rand @chars] for 1..15;
	
	if (! open(USER, '<', "$users_dir/$username")) {
		$errors .= "Username does not exist.<br />";
		return $errors;
	}
	
	open(LOST, ">$lostpass_dir/$username");
	print LOST "$key"; 
	close(LOST);
	
	my $userinfo = <USER>; 
	close(USER);
	my @usercomponents = split('\|', $userinfo); #as $usercomponents[7] is their email
	
	#email user auth key
	my $subject = "Recover your account | Mekong.com.au";
	my $heading = "Hey $username!";
	my $body = "You can recover your Mekong.com.au account by clicking on the link below:<br/>
				<a href=\"$script_url?action=recover&username=$username&authorization_key=$key\">$script_url?action=recover&username=$username&authorization_key=$key</a>";
	
	send_mail($username, $usercomponents[7], $subject, $heading, $body);

	return $errors;
}

#check if authorization information is correct
sub process_forgot_pass {
	my $provided_auth = param('authorization_key');
	my $username = param('username');
	my $errors = "";
	
	if (! open(LOST, "<$lostpass_dir/$username")) {#read in the info key for user
		$errors .= "A recovery email has not yet been requested for this user.<br />";
		return $errors;
	}
	
	my $key = <LOST>;
	close(AUTH);
	
	if (! defined $username) {
		$errors .= "Missing username parameter.";
		return $errors;
	}
	
	if ($provided_auth ne $key) {
		$errors .= "Incorrect authorization key provided";
		return $errors;
	}
	
	#if no errors detected
	unlink "$lostpass_dir/$username"; #remove recovery file

	return $errors;
}

#page where user can provide password
sub forgot_pass_2 {
	print logo();
	
	my $username = param('username');
	my $errors = $_[0] if defined $_[0];
	
	print "<h1>Enter New Password</h1>";
	
	#print errors if they exist
	if (defined $errors && $errors ne "") {
		print "<span class=\"error\">", $errors, "</span>";
	}

	print <<eof;
	<form method="post" class="center">
	<table align="center">
	<tr><td>Enter your new Password: </td> 
	<td>
	<input type="password" name="password"  width="10" maxlength="15" /></td></tr>
	<tr><td></td>
	<td>
	<input type="hidden" name="username"  value="$username" />
	<input class="btn" type="submit" name="action" value="Update Password"><br /><br />
	<input class="btn" type="submit" name="action" value="Cancel">
	</td></tr>
	</table>
	</form>
eof
}

#all checks completed, update the password!
sub process_forgot_pass_2 {
	my $username = param('username');
	my $password = param('password');
	my $errors = "";
	
	if ($password =~ /[^A-Za-z0-9@#$!%^&*]/) {
		$errors .=  "Invalid characters in password. Only A-Za-z0-9@#$!%^&* permitted.<br>";
	}
	if (length($password) < 6 || length($password) > 15) {
		$errors .=  "Password must be between 6 and 15 characters long.<br>";
	}
	
	if ($errors eq "") { #if no errors
		#hash encrypt password
		$password = md5hash($password);
		
		open(USER, '<', "$users_dir/$username");
		my $info = <USER>;
		close(USER);
		
		@userinfo = split('\|', $info); # userinfo[1] contains password
		$userinfo[1] = $password; #update password
		$info = join('|', @userinfo);
		
		open(USER, '>', "$users_dir/$username");
		print USER $info;
		close(USER);
	}
	
	return $errors;
}

#redirects user to homepage after recovery of password
sub redirect_lost_pass {
	my $username = param('username');
	print smalllogo();
	
	print <<eof
	<div class="center">
	<h1>Hey $username! Your password was just reset.</h1>
	<br />
	<p>Redirecting to homepage in 5 seconds...</p>
	<script type="text/JavaScript">
	<!--
	setTimeout("window.location=\'$script_url\'" ,5000);
	-->
	</script>
	</div>
eof
}

#######################
### Other functions ###
#######################


# return true if specified string could be an credit card number
sub legal_credit_card_number {
	my ($number) = @_;
	
	return 1 if $number =~ /^\d{16}$/;
	$last_error = "Invalid credit card number - must be 16 digits.\n";
	return 0;
}

# return true if specified string could be an credit card expiry date
sub legal_expiry_date {
	my ($expiry_date) = @_;
	
	return 1 if $expiry_date =~ /^\d\d\/\d\d$/;
	$last_error = "Invalid expiry date - must be mm/yy, e.g. 11/04.\n";
	return 0;
}


###
### Below here are utility functions
### Most are unused by the code above, but you will 
### need to use these functions (or write your own equivalent functions)
### 
###

# return true if specified string can be used as a login

sub legal_login {
	my ($login) = @_;
	our ($last_error);

	if ($login !~ /^[a-zA-Z][a-zA-Z0-9]*$/) {
		$last_error = "Invalid login '$login': logins must start with a letter and contain only letters and digits.";
		return 0;
	}
	if (length $login < 3 || length $login > 8) {
		$last_error = "Invalid login: logins must be 3-8 characters long.";
		return 0;
	}
	return 1;
}

# return true if specified string can be used as a password

sub legal_password {
	my ($password) = @_;
	our ($last_error);
	
	if ($password =~ /\s/) {
		$last_error = "Invalid password: password can not contain white space.";
		return 0;
	}
	if (length $password < 5) {
		$last_error = "Invalid password: passwords must contain at least 5 characters.";
		return 0;
	}
	return 1;
}


# return true if specified string could be an ISBN

sub legal_isbn {
	my ($isbn) = @_;
	our ($last_error);
	
	return 1 if $isbn =~ /^\d{9}(\d|X)$/;
	$last_error = "Invalid isbn '$isbn' : an isbn must be exactly 10 digits.";
	return 0;
}


# return total cost of specified books

sub total_books {
	my @isbns = @_;
	our %book_details;
	$total = 0;
	foreach $isbn (@isbns) {
		die "Internal error: unknown isbn $isbn  in total_books" if !$book_details{$isbn}; # shouldn't happen
		my $price = $book_details{$isbn}{price};
		$price =~ s/[^0-9\.]//g;
		$total += $price;
	}
	return $total;
}

# return true if specified login & password are correct
# user's details are stored in hash user_details

sub authenticate {
	my ($login, $password) = @_;
	our (%user_details, $last_error);
	
	return 0 if !legal_login($login);
	if (!open(USER, "$users_dir/$login")) {
		$last_error = "User '$login' does not exist.";
		return 0;
	}
	my %details =();
	while (<USER>) {
		next if !/^([^=]+)=(.*)/;
		$details{$1} = $2;
	}
	close(USER);
	foreach $field (qw(name street city state postcode password)) {
		if (!defined $details{$field}) {
 	 	 	$last_error = "Incomplete user file: field $field missing";
			return 0;
		}
	}
	if ($details{"password"} ne $password) {
  	 	$last_error = "Incorrect password.";
		return 0;
	 }
	 %user_details = %details;
  	 return 1;
}

# read contents of files in the books dir into the hash book
# a list of field names in the order specified in the file
 
sub read_books {
	my ($books_file) = @_;
	our %book_details;
	print STDERR "read_books($books_file)\n" if $debug;
	open BOOKS, $books_file or die "Can not open books file '$books_file'\n";
	my $isbn;
	while (<BOOKS>) {
		if (/^\s*"(\d+X?)"\s*:\s*{\s*$/) {
			$isbn = $1;
			next;
		}
		next if !$isbn;
		my ($field, $value);
		if (($field, $value) = /^\s*"([^"]+)"\s*:\s*"(.*)",?\s*$/) {
			$attribute_names{$field}++;
			print STDERR "$isbn $field-> $value\n" if $debug > 1;
			$value =~ s/([^\\]|^)\\"/$1"/g;
	  		$book_details{$isbn}{$field} = $value;
		} elsif (($field) = /^\s*"([^"]+)"\s*:\s*\[\s*$/) {
			$attribute_names{$1}++;
			my @a = ();
			while (<BOOKS>) {
				last if /^\s*\]\s*,?\s*$/;
				push @a, $1 if /^\s*"(.*)"\s*,?\s*$/;
			}
	  		$value = join("\n", @a);
			$value =~ s/([^\\]|^)\\"/$1"/g;
	  		$book_details{$isbn}{$field} = $value;
	  		print STDERR "book{$isbn}{$field}=@a\n" if $debug > 1;
		}
	}
	close BOOKS;
}


# return books in specified user's basket

sub read_basket {
	my ($login) = @_;
	our %book_details;
	open F, "$baskets_dir/$login" or return ();
	my @isbns = <F>;

	close(F);
	chomp(@isbns);
	!$book_details{$_} && die "Internal error: unknown isbn $_ in basket\n" foreach @isbns;
	return @isbns;
}


# delete specified book from specified user's basket
# only first occurance is deleted

sub delete_basket {
	my ($login, $delete_isbn) = @_;
	my @isbns = read_basket($login);
	open F, ">$baskets_dir/$login" or die "Can not open $baskets_dir/$login: $!";
	foreach $isbn (@isbns) {
		if ($isbn eq $delete_isbn) {
			$delete_isbn = "";
			next;
		}
		print F "$isbn\n";
	}
	close(F);
	unlink "$baskets_dir/$login" if ! -s "$baskets_dir/$login";
}


# add specified book to specified user's basket

sub add_basket {
	my ($login, $isbn) = @_;
	open F, ">>$baskets_dir/$login" or die "Can not open $baskets_dir/$login::$! \n";
	print F "$isbn\n";
	close(F);
}


# finalize specified order

sub finalize_order_old {
	my ($login, $credit_card_number, $expiry_date) = @_;
	my $order_number = 0;

	if (open ORDER_NUMBER, "$orders_dir/NEXT_ORDER_NUMBER") {
		$order_number = <ORDER_NUMBER>;
		chomp $order_number;
		close(ORDER_NUMBER);
	}
	$order_number++ while -r "$orders_dir/$order_number";
	open F, ">$orders_dir/NEXT_ORDER_NUMBER" or die "Can not open $orders_dir/NEXT_ORDER_NUMBER: $!\n";
	print F ($order_number + 1);
	close(F);

	my @basket_isbns = read_basket($login);
	open ORDER,">$orders_dir/$order_number" or die "Can not open $orders_dir/$order_number:$! \n";
	print ORDER "order_time=".time()."\n";
	print ORDER "credit_card_number=$credit_card_number\n";
	print ORDER "expiry_date=$expiry_date\n";
	print ORDER join("\n",@basket_isbns)."\n";
	close(ORDER);
	unlink "$baskets_dir/$login";
	
	open F, ">>$orders_dir/$login" or die "Can not open $orders_dir/$login:$! \n";
	print F "$order_number\n";
	close(F);
	
}


# return order numbers for specified login

sub login_to_orders {
	my ($login) = @_;
	open F, "$orders_dir/$login" or return ();
	@order_numbers = <F>;
	close(F);
	chomp(@order_numbers);
	return @order_numbers;
}



# return contents of specified order

sub read_order {
	my ($order_number) = @_;
	open F, "$orders_dir/$order_number" or warn "Can not open $orders_dir/$order_number:$! \n";
	@lines = <F>;
	close(F);
	chomp @lines;
	foreach (@lines[0..2]) {s/.*=//};
	return @lines;
}

###
### functions below are only for testing from the command line
### Your do not need to use these funtions
###

sub console_main {
	set_global_variables();
	$debug = 1;
	foreach $dir ($orders_dir,$baskets_dir,$users_dir) {
		if (! -d $dir) {
			print "Creating $dir\n";
			mkdir($dir, 0777) or die("Can not create $dir: $!");
		}
	}
	read_books($books_file);
	my @commands = qw(login new_account search details add drop basket checkout orders quit);
	my @commands_without_arguments = qw(basket checkout orders quit);
	my $login = "";
	
	print "mekong.com.au - ASCII interface\n";
	while (1) {
		$last_error = "";
		print "> ";
		$line = <STDIN> || last;
		$line =~ s/^\s*>\s*//;
		$line =~ /^\s*(\S+)\s*(.*)/ || next;
		($command, $argument) = ($1, $2);
		$command =~ tr/A-Z/a-z/;
		$argument = "" if !defined $argument;
		$argument =~ s/\s*$//;
		
		if (
			$command !~ /^[a-z_]+$/ ||
			!grep(/^$command$/, @commands) ||
			grep(/^$command$/, @commands_without_arguments) != ($argument eq "") ||
			($argument =~ /\s/ && $command ne "search")
		) {
			chomp $line;
			$line =~ s/\s*$//;
			$line =~ s/^\s*//;
			incorrect_command_message("$line");
			next;
		}

		if ($command eq "quit") {
			print "Thanks for shopping at mekong.com.au.\n";
			last;
		}
		if ($command eq "login") {
			$login = login_command($argument);
			next;
		} elsif ($command eq "new_account") {
			$login = new_account_command($argument);
			next;
		} elsif ($command eq "search") {
			search_command($argument);
			next;
		} elsif ($command eq "details") {
			details_command($argument);
			next;
		}
		
		if (!$login) {
			print "Not logged in.\n";
			next;
		}
		
		if ($command eq "basket") {
			basket_command($login);
		} elsif ($command eq "add") {
			add_command($login, $argument);
		} elsif ($command eq "drop") {
			drop_command($login, $argument);
		} elsif ($command eq "checkout") {
			checkout_command($login);
		} elsif ($command eq "orders") {
			orders_command($login);
		} else {
			warn "internal error: unexpected command $command";
		}
	}
}

sub login_command {
	my ($login) = @_;
	if (!legal_login($login)) {
		print "$last_error\n";
		return "";
	}
	if (!-r "$users_dir/$login") {
		print "User '$login' does not exist.\n";
		return "";
	}
	printf "Enter password: ";
	my $pass = <STDIN>;
	chomp $pass;
	if (!authenticate($login, $pass)) {
		print "$last_error\n";
		return "";
	}
	$login = $login;
	print "Welcome to mekong.com.au, $login.\n";
	return $login;
}

sub new_account_command {
	my ($login) = @_;
	if (!legal_login($login)) {
		print "$last_error\n";
		return "";
	}
	if (-r "$users_dir/$login") {
		print "Invalid user name: login already exists.\n";
		return "";
	}
	if (!open(USER, ">$users_dir/$login")) {
		print "Can not create user file $users_dir/$login: $!";
		return "";
	}
	foreach $description (@new_account_rows) {
		my ($name, $label)  = split /\|/, $description;
		next if $name eq "login";
		my $value;
		while (1) {
			print "$label ";
			$value = <STDIN>;
			exit 1 if !$value;
			chomp $value;
			if ($name eq "password" && !legal_password($value)) {
				print "$last_error\n";
				next;
			}
			last if $value =~ /\S+/;
		}
		$user_details{$name} = $value;
		print USER "$name=$value\n";
	}
	close(USER);
	print "Welcome to mekong.com.au, $login.\n";
	return $login;
}

sub search_command {
	my ($search_string) = @_;
	$search_string =~ s/\s*$//;
	$search_string =~ s/^\s*//;
	search_command1(split /\s+/, $search_string);
}

sub search_command1 {
	my (@search_terms) = @_;
	my @matching_isbns = search_books1(@search_terms);
	if ($last_error) {
		print "$last_error\n";
	} elsif (@matching_isbns) {
		print_books(@matching_isbns);
	} else {
		print "No books matched.\n";
	}
}

sub details_command {
	my ($isbn) = @_;
	our %book_details;
	if (!legal_isbn($isbn)) {
		print "$last_error\n";
		return;
	}
	if (!$book_details{$isbn}) {
		print "Unknown isbn: $isbn.\n";
		return;
	}
	print_books($isbn);
	foreach $attribute (sort keys %{$book_details{$isbn}}) {
		next if $attribute =~ /Image|=|^(|price|title|authors|productdescription)$/;
		print "$attribute: $book_details{$isbn}{$attribute}\n";
	}
	my $description = $book_details{$isbn}{productdescription} or return;
	$description =~ s/\s+/ /g;
	$description =~ s/\s*<p>\s*/\n\n/ig;
	while ($description =~ s/<([^">]*)"[^"]*"([^>]*)>/<$1 $2>/g) {}
	$description =~ s/(\s*)<[^>]+>(\s*)/$1 $2/g;
	$description =~ s/^\s*//g;
	$description =~ s/\s*$//g;
	print "$description\n";
}

sub basket_command {
	my ($login) = @_;
	my @basket_isbns = read_basket($login);
	if (!@basket_isbns) {
		print "Your shopping basket is empty.\n";
	} else {
		print_books(@basket_isbns);
		printf "Total: %11s\n", sprintf("\$%.2f", total_books(@basket_isbns));
	}
}

sub add_command {
	my ($login,$isbn) = @_;
	our %book_details;
	if (!legal_isbn($isbn)) {
		print "$last_error\n";
		return;
	}
	if (!$book_details{$isbn}) {
		print "Unknown isbn: $isbn.\n";
		return;
	}
	add_basket($login, $isbn);
}

sub drop_command {
	my ($login,$isbn) = @_;
	my @basket_isbns = read_basket($login);
	if (!legal_isbn($argument)) {
		print "$last_error\n";
		return;
	}
	if (!grep(/^$isbn$/, @basket_isbns)) {
		print "Isbn $isbn not in shopping basket.\n";
		return;
	}
	delete_basket($login, $isbn);
}

sub checkout_command {
	my ($login) = @_;
	my @basket_isbns = read_basket($login);
	if (!@basket_isbns) {
		print "Your shopping basket is empty.\n";
		return;
	}
	print "Shipping Details:\n$user_details{name}\n$user_details{street}\n$user_details{city}\n$user_details{state}, $user_details{postcode}\n\n";
	print_books(@basket_isbns);
	printf "Total: %11s\n", sprintf("\$%.2f", total_books(@basket_isbns));
	print "\n";
	my ($credit_card_number, $expiry_date);
	while (1) {
			print "Credit Card Number: ";
			$credit_card_number = <>;
			exit 1 if !$credit_card_number;
			$credit_card_number =~ s/\s//g;
			next if !$credit_card_number;
			last if $credit_card_number =~ /^\d{16}$/;
			last if legal_credit_card_number($credit_card_number);
			print "$last_error\n";
	}
	while (1) {
			print "Expiry date (mm/yy): ";
			$expiry_date = <>;
			exit 1 if !$expiry_date;
			$expiry_date =~ s/\s//g;
			next if !$expiry_date;
			last if legal_expiry_date($expiry_date);
			print "$last_error\n";
	}
	finalize_order($login, $credit_card_number, $expiry_date);
}

sub orders_command {
	my ($login) = @_;
	print "\n";
	foreach $order (login_to_orders($login)) {
		my ($order_time, $credit_card_number, $expiry_date, @isbns) = read_order($order);
		$order_time = localtime($order_time);
		print "Order #$order - $order_time\n";
		print "Credit Card Number: $credit_card_number (Expiry $expiry_date)\n";
		print_books(@isbns);
		print "\n";
	}
}

# print descriptions of specified books
sub print_books(@) {
	my @isbns = @_;
	print get_book_descriptions(@isbns);
}

# return descriptions of specified books
sub get_book_descriptions {
	my @isbns = @_;
	my $descriptions = "";
	our %book_details;
	foreach $isbn (@isbns) {
		die "Internal error: unknown isbn $isbn in print_books\n" if !$book_details{$isbn}; # shouldn't happen
		my $title = $book_details{$isbn}{title} || "";
		my $authors = $book_details{$isbn}{authors} || "";
		$authors =~ s/\n([^\n]*)$/ & $1/g;
		$authors =~ s/\n/, /g;
		$descriptions .= sprintf "%s %7s %s - %s\n", $isbn, $book_details{$isbn}{price}, $title, $authors;
	}
	return $descriptions;
}

sub set_global_variables {
	$base_dir = ".";
	$books_file = "$base_dir/books.json";
	$orders_dir = "$base_dir/orders";
	$baskets_dir = "$base_dir/baskets";
	$users_dir = "$base_dir/users";
	$auth_dir = "$base_dir/auth";
	$lostpass_dir = "$base_dir/lostpass";
	$script_url = url();
	$script_path = url();
	$script_path =~ s/\/[^\/]*$//;
	$last_error = "";
	%user_details = ();
	%book_details = ();
	%attribute_names = ();
	@new_account_rows = (
		  'login|Login:|10',
		  'password|Password:|10',
		  'name|Full Name:|50',
		  'street|Street:|50',
		  'city|City/Suburb:|25',
		  'state|State:|25',
		  'postcode|Postcode:|25',
		  'email|Email Address:|35'
		  );
}


sub incorrect_command_message {
	my ($command) = @_;
	print "Incorrect command: $command.\n";
	print <<eof;
Possible commands are:
login <login-name>
new_account <login-name>                    
search <words>
details <isbn>
add <isbn>
drop <isbn>
basket
checkout
orders
quit
eof
}
