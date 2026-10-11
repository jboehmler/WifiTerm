#ifndef TICKS_H
#define TICKS_H

extern TickType_t ticks_ms(int ms);
extern void task_wait_ms(int ms);
extern void task_wait_s(float s);
extern void endless_wait(char *optmsg);

#endif // TICKS_H
