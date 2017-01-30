def login_callback(request):
    try:
        sid = request.GET['sid'] # We used 'sid' to refer to our Shibboleth token ID
    except:
        return HttpResponse('No sid supplied, so login cannot continue.')
        
    try:
        # Check that the token is valid first (e.g. it was requested by the front end at some point) by reading it
        # from the login tokens table in the database
        sid_data = ShibLoginToken.objects.get(sid=sid)
    except ShibLoginToken.DoesNotExist:
        return HttpResponse('Invalid sid. Please try logging in again.')
        
    # As this is the callback, the Shibboleth attributes will be added to the HTTP request headers.
    # We can get this header data in Python using the following code. Note that all text is set to upper
    # case and all formatting from the attribute name is removed. The field name is then set to HTTP_ATTRIBUTENAMEHERE.
    try:
        eppn = request.META['HTTP_EPPN']
        groups = request.META['HTTP_UCLINTRANETGROUPS']
        cn = request.META['HTTP_CN']
        department = request.META['HTTP_DEPARTMENT']
        given_name = request.META['HTTP_GIVENNAME']
        surname = request.META['HTTP_SN']
    except:
        return HttpResponse(
            'No Shibboleth data. This page should not be accessed directly!')

    # Check if the user is in the internal whitelist
    white_listed = WhiteList.objects.filter(eppn=eppn).exists()
    # Groups is a custom Shibboleth attribute UCL adds to requests so that we can work out which type of user
    # has logged in. We also have a manual username white list to override this.
    if "engscifac-ug" not in groups.split(';') and not white_listed:
        login_response = {
            "result": "failure",
            "message": ("This system is available only"
                        " to members of the engineering faculty.")
            }
    # Create a user account for somebody in the system if they have never logged in before. This allows us
    # to tie an API key to a user account, and also display any user data we want in the UI.
    else:
        if User.objects.filter(email=eppn).exists():
            user = User.objects.get(email=eppn)
        else:
            User.objects.create_user(
                username=cn,
                email=eppn,
                password=utils.random_string(128),
                first_name=given_name,
                last_name=surname
            )
            user = User.objects.get(email=eppn)
            group_2 = Group.objects.get(name="Group_2")
            user.groups.add(group_2)
            user.save()
            up = UserProfile(user=user)
            up.department = department
            up.save()

    # Create a new login token for the user who just logged in
    token, created = Token.objects.get_or_create(user=user)
    token.save()
    
    # The JSON response to send back to the client via the push stream channel
    login_response = {
        "result": "success",
        "message": "Login successful",
        "email": user.email,
        "quota_left": user.user_profile.quota_left,
        'token': token.key,
        "societies": [
            [k.user.first_name, k.user.username] for k in
            user.user_profile.associated_society.all()
        ],
        "groups": [k.name for k in user.groups.all()]
    }
    # Delete the Shibboleth login token so that it can be used again if randomly generated in the future.
    try:
        t = ShibLoginToken.objects.get(user=user)
        if t.sid != sid:
            t.delete()
    except ShibLoginToken.DoesNotExist:
        print("User has never tried logging in before, so there was nothing to delete. Continuing...")

    try:
        token = ShibLoginToken.objects.get(sid=sid)
        token.status = 1
        token.user = user
        token.save()
    except Exception as e:
        print("Error updating token in database")
        print(e)

    url = STREAM_PUBLISH_URL + "/?id=" + sid
    # Dump the login data generated above to a JSON string then base 64 encode it ready to be sent
    # to the frontend.
    # Then post this base-64 data to the push stream module on the channel ID with the same name
    # as the Shib login token.
    try:
        login_response_str = json.dumps(login_response)
        b64 = base64.b64encode(login_response_str.encode('utf-8'))
        r = requests.post(url, data=b64)
        print(r.text)
    except Exception as e:
        print("Error sending the data to stream backend")
        print(e)

    # Write the login data to the page as a response (useful for testing, but in theory as soon as this
    # data is sent the popup window should be closed off by the frontend so the user should not ever even
    # see this)
    response = HttpResponse(content_type="text/html")
    response.write(login_response)
    return response