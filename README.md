# renrengpt

## deploy server
```bash
wget -q https://raw.githubusercontent.com/minximenes/renrengpt/main/server/deploy -O deployserver
sudo bash deployserver
```
## deploy client
```bash
# use port tcp/80, 443
wget -q https://raw.githubusercontent.com/minximenes/renrengpt/main/client/deploy -O deployclient
sudo bash deployclient
# install ssl
/etc/nginx/cert/renrengpt.cn.pem
/etc/nginx/cert/renrengpt.cn.key
```