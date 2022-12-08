# libraries
import pandas as pd
import numpy as np
from z3 import *

CO2_FRESH_AIR = 400             # CO2 concentration (ppm) of fresh air
TEMP_FRESH_AIR = 91.4           # Temperature (33 degree F) of the fresh air
CP_AIR = 1.026                  # Specific heat of fresh air
DEF_TEMP_SUPPLY_AIR =  55.4     # Default temperature (degree fahrenheit) of supply air (13 degree celsius)
COST_PER_KWH = 0.1137           # USD Cost per KWh

# returns attack vector (measurements to add for launching attack) based on the zone parameters
def attack_vector(zones, zone_occupant, zone_temp_setpoint, zone_volume, pp_co2, pp_heat, load, zone_co2_setpoint, control_time):
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
    
    temp_supply_air = [Real( 'temp_supply_air_' + str(i)) for i in range(num_zones)]
    temp_mixed_air = [Real( 'temp_mixed_air_' + str(i)) for i in range(num_zones)]
    co2_mixed_air = [Real( 'co2_mixed_air_' + str(i)) for i in range(num_zones)]
    total_zone_cost = Real('total_zone_cost')

    att_zone_occupant = [Int( 'att_zone_occupant_' + str(i)) for i in range(num_zones)]
    
    o = Optimize()
    
    o.add(att_zone_occupant[0] == 0)
    o.add(zone_cost[0] == 0)
    
    zone_v_vent_unit = [0, 31.66, 21.66, 45.33, 36.83]
    zone_v_temp_unit = [0, 36.52, 49.21, 499.65, 256.46]
    
    for i in range(num_zones):
        ################## CONTROL CONSTRAINST #################
        
        o.add(v_vent_air[i] == zone_v_vent_unit[i] * att_zone_occupant[i])
        o.add(v_temp_air[i] == zone_v_temp_unit[i] * att_zone_occupant[i])
        
    
        ############### v_mixed_air ###############################
        o.add(att_zone_occupant[i] * ((pp_co2[i] * 1000000) / zone_volume[i]) == 
              (zone_co2_setpoint[i] - (( 1 - ( v_mixed_air[i] ) / zone_volume[i]) * zone_co2_setpoint[i] + 
                                     ( v_mixed_air[i] * co2_mixed_air[i]) / zone_volume[i])))
    
        o.add(v_mixed_air[i] * (zone_temp_setpoint[i] - temp_supply_air[i]) * 0.3167 == att_zone_occupant[i] * (pp_heat[i] + load[i]))    
        o.add(v_mixed_air[i] == v_return_air[i] + v_fresh_air[i])
        o.add(co2_mixed_air[i] == zone_co2_setpoint[i] * (v_return_air[i] / v_mixed_air[i]) + CO2_FRESH_AIR * (v_fresh_air[i] / v_mixed_air[i]))
        o.add(temp_mixed_air[i] == zone_temp_setpoint[i] * (v_return_air[i] / v_mixed_air[i]) + TEMP_FRESH_AIR * (v_fresh_air[i] / v_mixed_air[i]))
    
        
        ############### temperature control algorithm ############
        o.add(temp_supply_air[i] == 55.4)

        ############### other constraints ########################
        o.add(v_return_air[i] >= 0)
        o.add(temp_supply_air[i] >= 55.4)
        
        ############## cost constraint ###########################
        o.add(zone_cost[i] == v_mixed_air[i] * (temp_mixed_air[i] - DEF_TEMP_SUPPLY_AIR) * 0.3167 * (control_time / 60000) * COST_PER_KWH )
        
        o.add(att_zone_occupant[i] >= 0)

        
        
    ################## ATTACK CONSTRAINST #################
    o.add(Sum(att_zone_occupant) == sum(zone_occupant))
    o.add(total_zone_cost == Sum(zone_cost))
    
    o.maximize(total_zone_cost)
    o.check()
    #print(o.check())
    
    ################ occupant attack vector ################
    
    for i in range(num_zones):
        v_vent_air[i] = float(Fraction(str(o.model()[v_vent_air[i]])))
        v_temp_air[i] = float(Fraction(str(o.model()[v_temp_air[i]])))
    
        v_mixed_air[i] = float(Fraction(str(o.model()[v_mixed_air[i]])))
        temp_mixed_air[i] = float(Fraction(str(o.model()[temp_mixed_air[i]])))
    
        temp_supply_air[i] = float(Fraction(str(o.model()[temp_supply_air[i]])))
    
        co2_mixed_air[i] = float(Fraction(str(o.model()[co2_mixed_air[i]])))
        v_return_air[i] = float(Fraction(str(o.model()[v_return_air[i]])))
        v_fresh_air[i] = float(Fraction(str(o.model()[v_fresh_air[i]])))
        
        zone_cost[i] = float(Fraction(str(o.model()[zone_cost[i]])))
        att_zone_occupant[i] = int(Fraction(str(o.model()[att_zone_occupant[i]])))
    
        
    total_zone_cost = float(Fraction(str(o.model()[total_zone_cost])))
    
    o.add(att_zone_occupant[4] <= 1)

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
#     print("att_zone_occupant",  att_zone_occupant)
# =============================================================================
    
    del_zone_occ = (np.asarray(att_zone_occupant) - np.asarray(zone_occupant)).tolist()
    del_zone_temp = [ Real('del_zone_temp' + str(i)) for i in range(num_zones)] 
    zone_co2 =  [Real('zone_co2' + str(i)) for i in range(num_zones)]
    
    s = Solver()
    
    for i in range(num_zones):
        
        s.add((del_zone_occ[i] * (pp_heat[i] + load[i]) * control_time * 60)/1000 == (zone_volume[i] * 0.036) * 1.006 * (del_zone_temp[i]))    
        s.add(del_zone_occ[i] * -1 * ((pp_co2[i] * 1000000) / zone_volume[i]) == 
              (zone_co2[i] - (( 1 - ( v_mixed_air[i] ) / zone_volume[i]) * zone_co2_setpoint[i] + 
                                     ( v_mixed_air[i] * co2_mixed_air[i]) / zone_volume[i])))
    
        
    #print(s.check())
    s.check()
    for i in range(num_zones):
        del_zone_temp[i] = float(Fraction(str(s.model()[del_zone_temp[i]])))
        zone_co2[i] = float(Fraction(str(s.model()[zone_co2[i]])))
    #print("zone_co2", zone_co2)   
    
    for i in range(len(del_zone_temp)):
        if del_zone_temp[i]:
            del_zone_temp[i] -= 32
            del_zone_temp[i] /= 1.8
    #print("del_zone_temp", del_zone_temp)
    del_zone_co2 = []
    for i in range(len(zone_co2)):
        if del_zone_occ[i]:
            del_zone_co2.append(zone_co2[i] - zone_co2_setpoint[i])
        else:
            del_zone_co2.append(0)
        
    #print("del_zone_co2", del_zone_co2)
    return att_zone_occupant, del_zone_occ, del_zone_temp, del_zone_co2