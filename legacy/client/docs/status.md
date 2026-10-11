Change term tasks to always run and not use print statements.  Term tasks should only put data into or take data out of queues.  Let central task handle the data in the queues and raw vs. command mode but NOT modify the terminal settings themselves.

Alternatively, see if moving actual mode changes into a one shot in the tasks would work.
