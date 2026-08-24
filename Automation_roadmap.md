Things that need to be implemented!!!!

1. main.py should include a step to ask permission to install nightly build via ansible : target [1]

2. need to verify that system is in production mode first before running any further checks ('systemctl get-default' see if 'prod.target' and not 'dev.target') : target [3]

3. need to be able to start squish servers on cockpit/cart pc [currently not implemented. this is absolutely required for automating squish]
<John did this>


4. Bootcheck run in order of perception->cart->cockpit->techPC
[the above gets up to item 9 in TEST_COVERAGE_ANALYSIS.md]
5. awaiting implementation [21]
6. after 'start surgery' instantiate timer locally, grab timer reading from cart and cockpit. after 10 second window, grab timer reading again. Compare and check lead/lag : target [23]

7. side/wide camera feed [Cockpit PC] (somehow needs bootcheck to verify 130 is pass, then confirm through squish hook that video stream is live) target [26, 27] 

8. Telecentricc camera [Cart PC GUI] - same logic as wide/side : target [28]

9. data_recorder [all PC] automate with shell script. target:g667 [30]

* yet to be implemented
need to consider how to verify OCT image


For testing, when I need to repeat some GUI actions, but cannot because the surgical sequence already advanced too far,
1. I need to kill all GUIs (assistant_gui.service / cart_gui.service on amon-cart, and surgeon_gui.service on amon-cockpit)
2. then I need to kill all system_manager.service on amon-cart, amon-cockpit (don't kill amon-perception unless something happens, video feed should be constant)
3. Start all system_manager.service on the cart and cockpit PCs
4. start the GUI services, namely (assistant_gui.service / cart_gui.service on amon-cart, and surgeon_gui.service on amon-cockpit)

The commands for step 1 to 4 is the following:
1. sudo systemctl kill cart_gui.service assistant_gui.service (this is on amon-cart)
   sudo systemctl kill surgeon_gui.service (this is on amon-cockpit)
2. sudo systemctl kill system_manager.services (on amon-cart, amon-cockpit)
3. sudo systemctl start system_manager.services (on amon-cart, amon-cockpit)
4. sudo systemctl start cart_gui.service assistant_gui.service (this is on amon-cart)
   sudo systemctl start surgeon_gui.service (this is on amon-cockpit)
