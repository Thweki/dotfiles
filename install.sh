#!/bin/env sh
all_file=$(find | grep -vP '(^\./\.git/?|^\.$|^\./install\.sh$|^\./\.config$|^\./\.config/.*/)')

source_name=$(echo "$all_file"|sed "s#^\./#$(pwd)/#")
target_name=$(echo "$all_file"|sed "s#^\.#$HOME#")

source_list=(); while read -r line;do source_list+=($line);done <<< $source_name
target_list=(); while read -r line;do target_list+=($line);done <<< $target_name

for ((num=0;num<${#source_list[@]};num++)); do
    ln -sfnv ${source_list[num]}  ${target_list[num]}
    #echo " ${source_list[num]} > ${target_list[num]}"
done
