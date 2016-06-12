#!/usr/bin/env python3
#
# Simple pyprofibus example
#
# This example initializes an ET-200S slave, reads input
# data and writes the data back to the module.
#
# The hardware configuration is as follows:
#
#   v--------------v----------v----------v----------v----------v
#   |     IM 151-1 | PM-E     | 2 DO     | 2 DO     | 4 DI     |
#   |     STANDARD | DC24V    | DC24V/2A | DC24V/2A | DC24V    |
#   |              |          |          |          |          |
#   |              |          |          |          |          |
#   | ET 200S      |          |          |          |          |
#   |              |          |          |          |          |
#   |              |          |          |          |          |
#   |       6ES7   | 6ES7     | 6ES7     | 6ES7     | 6ES7     |
#   |       151-   | 138-     | 132-     | 132-     | 131-     |
#   |       1AA04- | 4CA01-   | 4BB30-   | 4BB30-   | 4BD01-   |
#   |       0AB0   | 0AA0     | 0AA0     | 0AA0     | 0AA0     |
#   ^--------------^----------^----------^----------^----------^
#

import sys
import pyprofibus, pyprofibus.phy_serial
from pyprofibus import DpTelegram_SetPrm_Req, monotonic_time


master = None
try:
	# Parse the GSD file.
	# And select the plugged modules.
	gsd = pyprofibus.GsdInterp.fromFile("si03806a.gse", debug = False)
	gsd.setConfiguredModule("6ES7 138-4CA01-0AA0 PM-E DC24V")
	gsd.setConfiguredModule("6ES7 132-4BB30-0AA0  2DO DC24V")
	gsd.setConfiguredModule("6ES7 132-4BB30-0AA0  2DO DC24V")
	gsd.setConfiguredModule("6ES7 131-4BD01-0AA0  4DI DC24V")

	# Create a PHY (layer 1) interface object
	phy = pyprofibus.phy_serial.CpPhySerial(port = "/dev/ttyS0",
						debug = False)
	phy.setConfig(19200)

	# Create a DP class 1 master with DP address 1
	master = pyprofibus.DPM1(phy = phy,
				 masterAddr = 2,
				 debug = True)

	# Create a slave description for an ET-200S.
	# The ET-200S has got the DP address 8 set via DIP-switches.
	et200s = pyprofibus.DpSlaveDesc(identNumber = gsd.getIdentNumber(),
					slaveAddr = 8)

	# Create Chk_Cfg telegram
	et200s.setCfgDataElements(gsd.getCfgDataElements())

	# Set User_Prm_Data
	dp1PrmMask = bytearray((DpTelegram_SetPrm_Req.DPV1PRM0_FAILSAFE,
				DpTelegram_SetPrm_Req.DPV1PRM1_REDCFG,
				0x00))
	dp1PrmSet  = bytearray((DpTelegram_SetPrm_Req.DPV1PRM0_FAILSAFE,
				DpTelegram_SetPrm_Req.DPV1PRM1_REDCFG,
				0x00))
	et200s.setUserPrmData(gsd.getUserPrmData(dp1PrmMask = dp1PrmMask,
						 dp1PrmSet = dp1PrmSet))

	# Set various standard parameters
	et200s.setSyncMode(True)		# Sync-mode supported
	et200s.setFreezeMode(True)		# Freeze-mode supported
	et200s.setGroupMask(1)			# Group-ident 1
	et200s.setWatchdog(300)			# Watchdog: 300 ms

	# Register the ET-200S slave at the DPM
	master.addSlave(et200s)

	# Initialize the DPM
	master.initialize()

	# Cyclically run Data_Exchange.
	# 4 input bits from the 4-DI module are copied to
	# the two 2-DO modules.
	inData = 0
	rtSum, runtimes, nextPrint = 0, [ 0, ] * 512, monotonic_time() + 1.0
	while True:
		start = monotonic_time()

		# Run slave state machine.
		outData = [inData & 3, (inData >> 2) & 3]
		inDataTmp = master.runSlave(et200s, outData)
		if inDataTmp is not None:
			inData = inDataTmp[0]

		# Print statistics.
		end = monotonic_time()
		runtimes.append(end - start)
		rtSum = rtSum - runtimes.pop(0) + runtimes[-1]
		if end > nextPrint:
			nextPrint = end + 3.0
			sys.stderr.write("pyprofibus cycle time = %.3f ms\n" %\
				(rtSum / len(runtimes) * 1000.0))

except pyprofibus.ProfibusError as e:
	print("Terminating: %s" % str(e))
finally:
	if master:
		master.destroy()
