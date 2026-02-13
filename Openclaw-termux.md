

pkg install npm
NODE_LLAMA_CPP_SKIP_DOWNLOAD=true npm i -g openclaw
~/.../openclaw/dist $ realpath entry.js                        /data/data/com.termux/files/home/.npm-global/lib/node_modules/openclaw/dist/entry.js                                          ~/.../openclaw/dist $ vim entry.js
~/.../openclaw/dist $ realpath entry.js                        
/data/data/com.termux/files/home/.npm-global/lib/node_modules/openclaw/dist/entry.js                                         
~/.../openclaw/dist $ vim entry.js

const DEFAULT_LOG_DIR = "./tmp/openclaw";

grep -rl '"\/tmp\/openclaw' --include="*.js" . | xargs sed -i 's|"/tmp/openclaw|"~/tmp/openclaw|g'

grep -rlF '"/bin/npm' --include="*.js" . | xargs sed -i 's|"/bin/npm|"~/bin/npm|g'



find . -type f -name "*.js" -exec cp {} {}.bak \; -exec sed -i 's|/tmp/openclaw|~/tmp/openclaw|g' {} \;

termux-setup-storage

~ $ ls storage/

audiobooks  downloads/  movies/     podcasts/

dcim/       external-0/ music/      shared/

documents/  media-0/    pictures/