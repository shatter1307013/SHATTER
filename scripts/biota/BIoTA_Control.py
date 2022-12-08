# libraries
import pandas as pd
import numpy as np
from z3 import *

CO2_FRESH_AIR = 400             # CO2 concentration (ppm) of fresh air
TEMP_FRESH_AIR = 91.4           # Temperature (33 degree F) of the fresh air
CP_AIR = 1.026                  # Specific heat of fresh air
DEF_TEMP_SUPPLY_AIR =  55.4     # Default temperature (degree fahrenheit) of supply air (13 degree celsius)
COST_PER_KWH = 0.1137           # USD Cost per KWh

# returns energy cost ($) based on the zone parameters at current timeslots
def control_cost (zones, zone_occupant, zone_temp_setpoint, zone_volume, pp_co2, pp_heat, load, zone_co2_setpoint, control_time):
    '''
    PARAMETERS:
    zones: zone information
    zone_occupant: list of occupants in different zones
    zone_temp_setpoint: list of temperature (fahrenheit) setpoint of the different zones
    zone_volume: # Zones' volumes (cubic feet)
    pp_co2: CO2 Emission by Occupant (cfm)
    pp_heat: Heat Radiation by Occupant (W)
    load: Heat radiated by Appliances (W)
    zone_co2_setpoint: list of CO2 (ppm) setpoint of the corresponding zones
    control_time: time of control operation (in minute)
    '''
    num_zones = len(zones)
    # initializing z3 variables
    v_vent_air = [Real( 'v_vent_air_' + str(i)) for i in range(num_zones)]   # Air required for ventillation (CFM)
    v_temp_air = [Real( 'v_temp_air_' + str(i)) for i in range(num_zones)]   # Air required for cooling (CFM)
    v_mixed_air = [Real( 'v_mixed_air_' + str(i)) for i in range(num_zones)]
    v_fresh_air = [Real( 'v_fresh_air_' + str(i)) for i in range(num_zones)]
    v_return_air = [Real( 'v_return_air_' + str(i)) for i in range(num_zones)]
    zone_cost = [Real( 'zone_cost' + str(i)) for i in range(num_zones)] 
    
    temp_supply_air = [ Real( 'temp_supply_air_' + str(i)) for i in range(num_zones)]
    temp_mixed_air = [ Real( 'temp_mixed_air_' + str(i)) for i in range(num_zones)]
    co2_mixed_air = [ Real( 'co2_mixed_air_' + str(i)) for i in range(num_zones)]
    total_zone_cost = Real('total_zone_cost')

    s = Solver()
    
    for i in range(1, num_zones):
        ############### v_vent_air ###############################
        s.add(zone_occupant[i] * ((pp_co2[i] * 1000000) / zone_volume[i]) == 
                       (zone_co2_setpoint[i] - (( 1 - (v_vent_air[i]) /zone_volume[i]) * zone_co2_setpoint[i] +  
                                                (v_vent_air[i] * CO2_FRESH_AIR) /  zone_volume[i])))
        
        ############### v_temp_air ###############################
        s.add(v_temp_air[i] *  (zone_temp_setpoint[i] - DEF_TEMP_SUPPLY_AIR) * 0.3167 == zone_occupant[i] * (pp_heat[i] + load[i])) 
    
        ############### v_mixed_air ###############################
        s.add(zone_occupant[i] * ((pp_co2[i] * 1000000) / zone_volume[i]) == 
              (zone_co2_setpoint[i] - (( 1 - ( v_mixed_air[i] ) / zone_volume[i]) * zone_co2_setpoint[i] + 
                                     ( v_mixed_air[i] * co2_mixed_air[i]) / zone_volume[i])))
    
        s.add( v_mixed_air[i] * (zone_temp_setpoint[i] - temp_supply_air[i]) * 0.3167 == zone_occupant[i] * (pp_heat[i] + load[i]))    
        s.add(v_mixed_air[i] == v_return_air[i] + v_fresh_air[i])
        s.add(co2_mixed_air[i] == zone_co2_setpoint[i] * (v_return_air[i] / v_mixed_air[i]) + CO2_FRESH_AIR * (v_fresh_air[i] / v_mixed_air[i]))
        s.add(temp_mixed_air[i] == zone_temp_setpoint[i] * (v_return_air[i] / v_mixed_air[i]) + TEMP_FRESH_AIR * (v_fresh_air[i] / v_mixed_air[i]))
    
        ############### temperature control algorithm ############
        s.add(Implies(v_vent_air[i] >= v_temp_air[i] , v_return_air[i] == 0))
        s.add(Implies(v_vent_air[i] < v_temp_air[i] ,  temp_supply_air[i] == 55.4))
    
        ############### other constraints ########################
        s.add(v_return_air[i] >= 0)
        s.add(temp_supply_air[i] >= 55.4)
        
        ############## cost constraint ###########################
        s.add(zone_cost[i] == v_mixed_air[i] * (temp_mixed_air[i] - DEF_TEMP_SUPPLY_AIR) * 0.3167 * (control_time / 60000) * COST_PER_KWH )
    s.add(total_zone_cost == Sum(zone_cost[1:]))
    s.check()
    
    for i in range(1, num_zones):
        v_vent_air[i] = float(Fraction(str(s.model()[v_vent_air[i]])))
        v_temp_air[i] = float(Fraction(str(s.model()[v_temp_air[i]])))
    
        v_mixed_air[i] = float(Fraction(str(s.model()[v_mixed_air[i]])))
        temp_mixed_air[i] = float(Fraction(str(s.model()[temp_mixed_air[i]])))
    
        temp_supply_air[i] = float(Fraction(str(s.model()[temp_supply_air[i]])))
    
        co2_mixed_air[i] = float(Fraction(str(s.model()[co2_mixed_air[i]])))
        v_return_air[i] = float(Fraction(str(s.model()[v_return_air[i]])))
        v_fresh_air[i] = float(Fraction(str(s.model()[v_fresh_air[i]])))
        
        zone_cost[i] = float(Fraction(str(s.model()[zone_cost[i]])))
    total_zone_cost = float(Fraction(str(s.model()[total_zone_cost])))
        
# =============================================================================
#     print("v_vent_air", v_vent_air)
#     print("v_temp_air", v_temp_air)
#     print("v_mixed_air", v_mixed_air)
#     print("v_return_air", v_return_air)
#     print("v_fresh_air", v_fresh_air)
#     print("temp_supply_air", temp_supply_air)
#     print("temp_mixed_air", temp_mixed_air)
#     print("co2_mixed_air", co2_mixed_air)
#     print("v_fresh_air", v_fresh_air)
#     print("zone_cost", zone_cost)
#     print("total_zone_cost", total_zone_cost)
# =============================================================================
    return total_zone_cost