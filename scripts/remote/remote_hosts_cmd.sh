#!/usr/bin/env bash

printf '%s\n' 'subash_1' | sudo -S /bin/sh -c "grep -q 'app.acme.local' /etc/hosts || echo '127.0.0.1 app.acme.local api.acme.local admin.acme.local storage.acme.local' >> /etc/hosts"
getent hosts app.acme.local api.acme.local admin.acme.local storage.acme.local
