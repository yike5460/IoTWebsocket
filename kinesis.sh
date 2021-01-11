# !/bin/bash
function rand(){
    min=$1
    max=$(($2-$min+1))
    num=$(($RANDOM+100000000))
    echo $(($num%$max+$min))
}

i=0;
while true; do i=$[$i+1]; echo {\"deviceID\": \"id-$(rand 10000 10005)\", \"value\": \"$(rand 50 100)\", \"time\": \"$(date "+%Y%m%d%H%M")\"} > /tmp/app.logtime.$i; sleep 5; done
