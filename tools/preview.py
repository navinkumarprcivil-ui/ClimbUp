#!/usr/bin/env python3
"""Build build/preview.html — the real bundle with the Google sign-in stubbed.

Screenshot and test only; never deployed. The auth gate covers every screen
until Firebase signs a real user in, which cannot happen in a headless
container, so this pins authState to 'signedIn' and stops componentDidMount
calling Firebase at all. index.html is not touched.

    python3 tools/bundle.py pack && python3 tools/preview.py
    python3 -m http.server 8000 --directory build
"""
import json
import os

from bundle import BUILD, TEMPLATE, load, write_island

OUT = os.path.join(BUILD, 'preview.html')

SUBS = [
    ("authState:'checking'", "authState:'signedIn'"),
    ("authUser:null, authError:null,",
     "authUser:{uid:'preview', email:'you@example.com'}, authError:null,"),
    ('if(window.__firebaseReady){', 'if(false){'),
]

if __name__ == '__main__':
    template = open(TEMPLATE, encoding='utf-8').read()
    for old, new in SUBS:
        assert old in template, 'preview stub missed: %s' % old
        template = template.replace(old, new, 1)
    # the else-branch of the now-dead firebase check still forces signedOut
    template = template.replace("""    }else{
      this.setState({authState:'signedOut'});
    }""", "    }else{ /* preview: stay signed in */ }", 1)

    encoded = json.dumps(template, ensure_ascii=False).replace('</', '<\\u002F')
    open(OUT, 'w', encoding='utf-8').write(write_island(load(), 'template', encoded))
    print('wrote', OUT)
