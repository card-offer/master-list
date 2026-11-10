import re,html,sys
s=open(sys.argv[1]).read()
m=re.search(r'<main.*?</main>',s,flags=re.S)
s=m.group(0) if m else s
t=re.sub(r'<script.*?</script>|<style.*?</style>','',s,flags=re.S)
t=re.sub(r'<a [^>]*href="([^"]+)"[^>]*>',r' [\1] ',t)
t=re.sub(r'<[^>]+>','\n',t); t=html.unescape(t)
print('\n'.join(l.strip() for l in t.split('\n') if l.strip()))
