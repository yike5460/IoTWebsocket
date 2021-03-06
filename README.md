# ETL工具（新增）
用作将如下所示特定数据A格式转换成数据B格式。

数据A格式（产品所用）

![productData](./media/productData.png "productData")

数据B格式（方案所用）

![solutionData](./media/solutionData.png "solutionData")

具体用法执行 DataAdapter.py，第一个参数为原始数据所在的s3桶，第二个参数为转换完毕后数据所上传的s3桶
```
# python3 DataAdapter.py -h
usage: python DataAdapter.py -i <s3 url of inputFile>, -o <s3 url of outputFile>, format like like s3://bucket/prefix/file.json
# python3 DataAdapter.py -i s3://aaronsfileshare/CSDC/original.json -o s3://aaronsfileshare/CSDC/final.csv
```

# IoTWebsocket整体架构
用户通过连接API Gateway实现的Websocket获取后端Kinesis Data Stream的实时数据和历史数据
![architecture](./media/architecture.png "architecture")

基本演示效果如下

![demo](./media/websocket_dashboard.gif "demo")

# 部署环境
点击进入CloudFormation界面，选择cfn.yaml进行部署除connect/disconnect外的所有服务，包括API Gateway，Lambda，Kinesis，IAM。
部署完毕后，手动进行如下步骤（未来会通过CloudFormation自动化）
- 部署Lambda函数实现Websocket连接的connect/disconnect功能，其中代码部分直接拷贝src目录下的connect.py和disconnect.py
- 进入API Gateway界面，将route下的@connect和@disconnect对接上一步创建好的Lambda函数
- 进入DynamoDB界面，创建IoTconnection表项，其中key为connectionId

# 测试环境

**登入环境**
```
ssh -i "china-general.pem" ec2-user@ec2-68-xx-xx-158.cn-northwest-1.compute.amazonaws.com.cn
```
**脚本自动生成随机文件**
```
[root@ip-172-31-21-238 ec2-user]# cat kinesis.sh 
# !/bin/bash
function rand(){
    min=$1
    max=$(($2-$min+1))
    num=$(($RANDOM+100000000))
    echo $(($num%$max+$min))
}

i=0;
while true; do i=$[$i+1]; echo {\"deviceID\": \"id-$(rand 10000 10005)\", \"value\": \"$(rand 50 100)\", \"time\": \"$(date "+%Y%m%d%H%M")\"} > /tmp/app.logtime.$i; sleep 5; done

[root@ip-172-31-21-238 ec2-user]# ls /tmp/app.logtime.* | wc -l
532
```

**安装agent**

参照https://docs.aws.amazon.com/firehose/latest/dev/writing-with-agents.html#download-install
```
sudo yum install –y aws-kinesis-agent
```

**配置agent**
```
[root@ip-172-31-21-238 ec2-user]# cat /etc/aws-kinesis/agent.json
{
  "cloudwatch.emitMetrics": true,
  "kinesis.endpoint": "kinesis.cn-northwest-1.amazonaws.com.cn",
  "firehose.endpoint": "",
  "maxBufferSizeRecords": "1",
  
  "flows": [
    {
      "filePattern": "/tmp/app.log*",
      "kinesisStream": "IoTPython-EventStream-5V9OW0KOLAE8",
      "partitionKeyOption": "RANDOM"
    }
  ]
}

[root@ip-172-31-21-238 ec2-user]# cat /etc/sysconfig/aws-kinesis-agent
# Set AWS credentials for accessing Amazon Kinesis Stream and Amazon Kinesis Firehose
#
AWS_ACCESS_KEY_ID=xxxx
AWS_SECRET_ACCESS_KEY=xxxx
AWS_DEFAULT_REGION=cn-northwest-1
#
# AGENT_ARGS=""
# AGENT_LOG_LEVEL="INFO"
```

**启动agent并查看状态**
```
[root@ip-172-31-21-238 ec2-user]# service aws-kinesis-agent start
[root@ip-172-31-21-238 ec2-user]# service aws-kinesis-agent status
● aws-kinesis-agent.service - LSB: Daemon for Amazon Kinesis Agent.
   Loaded: loaded (/etc/rc.d/init.d/aws-kinesis-agent; bad; vendor preset: disabled)
   Active: active (running) since Thu 2021-01-07 11:08:17 UTC; 13h ago
     Docs: man:systemd-sysv-generator(8)
  Process: 6892 ExecStop=/etc/rc.d/init.d/aws-kinesis-agent stop (code=exited, status=0/SUCCESS)
  Process: 7174 ExecStart=/etc/rc.d/init.d/aws-kinesis-agent start (code=exited, status=0/SUCCESS)
   CGroup: /system.slice/aws-kinesis-agent.service
           ├─7180 runuser aws-kinesis-agent-user -s /bin/sh -c /usr/bin/start-aws-kinesis-agent  
           └─7182 /usr/lib/jvm/jre/bin/java -server -Xms32m -Xmx512m -Dlog4j.configurationFile=file:///etc/aws-k...

Jan 07 11:08:15 ip-172-31-21-238.cn-northwest-1.compute.internal systemd[1]: Starting LSB: Daemon for Amazon Ki....
Jan 07 11:08:15 ip-172-31-21-238.cn-northwest-1.compute.internal runuser[7180]: pam_unix(runuser:session): sess...)
Jan 07 11:08:17 ip-172-31-21-238.cn-northwest-1.compute.internal aws-kinesis-agent[7174]: [34B blob data]
Jan 07 11:08:17 ip-172-31-21-238.cn-northwest-1.compute.internal systemd[1]: Started LSB: Daemon for Amazon Kin....
Hint: Some lines were ellipsized, use -l to show in full.

[root@ip-172-31-21-238 ~]# tail -f /var/log/aws-kinesis-agent/aws-kinesis-agent.log
2021-01-08 00:57:16.987+0000  (FileTailer[kinesis:IoTPython-EventStream-5V9OW0KOLAE8:/tmp/app.log*].MetricsEmitter RUNNING) com.amazon.kinesis.streaming.agent.tailing.FileTailer [INFO] FileTailer[kinesis:IoTPython-EventStream-5V9OW0KOLAE8:/tmp/app.log*]: Tailer Progress: Tailer has parsed 492 records (7872 bytes), transformed 0 records, skipped 0 records, and has successfully sent 492 records to destination.
2021-01-08 00:57:16.995+0000  (Agent.MetricsEmitter RUNNING) com.amazon.kinesis.streaming.agent.Agent [INFO] Agent: Progress: 492 records parsed (7872 bytes), and **492 records sent successfully to destinations**. Uptime: 49740037ms
```

**连接API Gateway创建好的Websocket**

连接成功后，可以看到有对应随机文件内容的持续输出，输入kinesisFetch可以查看到历史数据（固定为1小时前到当前的kinesis数据）
```
wscat -c wss://2ei2kyn7u6.execute-api.cn-northwest-1.amazonaws.com.cn/v1
< {"deviceID": "id-10000", "value": "92", "time": "202101111046"}

< {"deviceID": "id-10002", "value": "60", "time": "202101111046"}

< {"deviceID": "id-10003", "value": "69", "time": "202101111046"}

< {"deviceID": "id-10004", "value": "82", "time": "202101111046"}

< {"deviceID": "id-10003", "value": "69", "time": "202101111047"}

< {"deviceID": "id-10002", "value": "73", "time": "202101111047"}

> kinesisFetch
```

**登陆dashboard查看实时数据**
IoT通过[d3js](https://d3js.org/)实现动态展示
```
python -m http.server
Serving HTTP on 0.0.0.0 port 8000 (http://0.0.0.0:8000/) ...
127.0.0.1 - - [11/Jan/2021 18:37:03] "GET / HTTP/1.1" 304 -
```













