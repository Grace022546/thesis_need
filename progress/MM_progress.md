目前MM其實已經做過不少優化：

output-stationary；
B-stationary，B向量常駐local SRAM；
A row使用full-K burst；
兩組accumulator context交錯；
A buffer／accumulator ping-pong；
最後才做reduction、RU pack與writeback。

所以MM64已經有 82.1% mapped PE arithmetic utilization。接下來最值得救的是MM8與MM16，而不是推翻整個mapping。
