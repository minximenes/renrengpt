# renrengpt

## deploy server
```bash
# use port tcp/81
wget -q https://raw.githubusercontent.com/minximenes/renrengpt/main/server/deploy -O deployserver
sudo bash deployserver
```
## deploy client
```bash
# use port tcp/80
wget -q https://raw.githubusercontent.com/minximenes/renrengpt/main/client/deploy -O deployclient
sudo bash deployclient
```

https://www.alibabacloud.com/help/zh/ram/user-guide/create-an-accesskey-pair

为什么实例明细页面正常显示，但是启动日志查看不了，初始化脚本的服务也连不上？
实例从资源准备到启动完毕大约需要１分钟时间，请在创建时间的１分钟后点击查看启动日志，并尝试连接
初始化脚本中运行的服务。