# Go bounded gateway

A controlled Go concurrency study comparing FIFO scheduling with a generated shortest-delay policy. A readable gateway authority enforces worker, queue, deadline, malformed-input, and completion bounds. The generated policy can reorder only; it cannot bypass admission or cancellation.

`make check` runs unit tests, the race detector, and a bounded fuzz smoke. Formal MNCS and MNCDS status remain `UNKNOWN` pending protected evaluation, repeated performance evidence, checkpoint drill, and independent reproduction.
