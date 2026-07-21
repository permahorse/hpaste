#TBD req = urllib2.Request(r'https://paste.fedoraproject.org/api/paste/submit', json.dumps({'contents':'qweqweqwe test123', 'expiry_time':'%d'%(time.time()+6000), 'title':'test1'}), headers={'Content-Type':'application/json'})
# urllib2.urlopen(json.loads(rep.read())['url']+'/raw').read()
# cool
