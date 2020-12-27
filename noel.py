#!/usr/bin/env python3

import glob, os
import math
import time

# Colours stolen from proute (github/fa-bien/proute)
# generic colour encapsulation class
# arbitrary decision = components take integer values between 0 and 255
class Colour():
    def __init__(self, red, green, blue, alpha=255):
        self.red = red
        self.green = green
        self.blue = blue
        self.alpha = alpha

    # allows to recreate the object
    def __repr__(self):
        return self.__module__ + '.Colour(' + str(self.red) + ',' + \
            str(self.green) + ',' + str(self.blue) + ',' + str(self.alpha) + ')'

# stolen and adapted from proute
# create a RGB colour from HSV values
# H in [0, 1), S in [0, 1], V in [0, 1]
class HSVColour(Colour):
    def __init__(self, H, S, V):
        self.setHSV(H, S, V)

    def setHSV(self, H, S, V):
        self.H, self.S, self.V = H, S, V

    def getRGBAColour(self):
        C = self.V * self.S
        Hprime = self.H * 6
        X = C * (1 - math.fabs(Hprime % 2 - 1))
        if Hprime < 1:
            R, G, B = C, X, 0
        elif Hprime < 2:
            R, G, B = X, C, 0
        elif Hprime < 3:
            R, G, B = 0, C, X
        elif Hprime < 4:
            R, G, B = 0, X, C
        elif Hprime < 5:
            R, G, B = X, 0, C
        elif Hprime < 6:
            R, G, B = C, 0, X
        else:
            print('incorrect H, S, V values:', self.H, self.S, self.V)
        m = self.V - C
        return Colour(int(255 * (R + m)),
                      int(255 * (G + m)),
                      int(255 * (B + m)))

# also stolen from proute
# generate k colours spread using H,S,V space and golden ratio
# distance is the hue distance between two consecutive colours in the spread
# a value of -1 means use the silver ratio, which is a good way to delay as
# much as possible having two similar colours
def generateSpreadColours(k, distance=-1):
    # our first colour: a bright blue
    H, S, V = .6, .99, .7
    if distance == -1:
        distance = 2.0 / (1 + math.sqrt(5))
    return [ HSVColour((H + distance * x) % 1, S, V) for x in range(k) ]

def finddevices():
    devices = []
    # find all leds that end in 'red'
    redleds = glob.glob('/sys/class/leds/*red')
    for rl in redleds:
        if os.path.isdir(rl.replace('red', 'green')) and \
           os.path.isdir(rl.replace('red', 'blue')):
            devices.append(rl.replace(':red', ''))
    return devices

# colour is a Colour object
def setcolour(device, colour):
    with open(device + ':red/brightness', 'w') as red:
        red.write(str(colour.red))
    with open(device + ':green/brightness', 'w') as green:
        green.write(str(colour.green))
    with open(device + ':blue/brightness', 'w') as blue:
        blue.write(str(colour.blue))

# an effect to apply to a bunch of colours
class Effect:
    # may be overloaded
    def __init__(self):
        pass

    # apply one step of this effect to all passed colours
    # must be overloaded
    def step(self, colours):
        pass

    def reset(self):
        pass

# cycle: at each step add given step values to H, S and V colour components
class HSVCycleEffect(Effect):
    def __init__(self, H=.05, S=0, V=0, minS=1/255, maxS=1, minV=1/255, maxV=1):
        self.dH, self.dS, self.dV = H, S, V
        self.nsteps = 0
        self.minS, self.maxS, self.Srange = minS, maxS, maxS - minS
        self.minV, self.maxV, self.Vrange = minV, maxV, maxV - minV
        
    def step(self, colours):
        if self.nsteps == 0:
            self.Sinit = [ math.asin(c.S) for c in colours ]
            self.Vinit = [ math.asin(c.V) for c in colours ]
        self.nsteps += 1
        for c, S, V in zip(colours, self.Sinit, self.Vinit):
            c.H = (c.H + self.dH) % 1
            c.S = self.minS + self.Srange * \
                (1 + math.sin(S + self.dS * self.nsteps)) / 2.0
            c.V = self.minV + self.Vrange * \
                (1 + math.sin(V + self.dV * self.nsteps)) / 2.0

# combined effects! combine several effects
class CombinedEffects(Effect):
    def __init__(self, effects):
        self.effects = effects

    def step(self, colours):
        for effect in self.effects:
            effect.step(colours)

import random
# Random effect to make people (or cats) puke
class RandomEffect(Effect):
    def step(self, colours):
        for c in colours:
            c.H = random.random()

# fade colour out then in another colour, over a list of predefined hues
class ChristmasEffect(Effect):
    def __init__(self, V=0.1, minV=1/255, maxV=0.7, hues=[ 0, 51/360, 0.33]):
        self.dV = V
        self.minV, self.maxV, self.Vrange = minV, maxV, maxV - minV
        self.hues = hues
        self.nsteps = 0
        self.switched = False
            
    def step(self, colours):
        if self.nsteps == 0:
            self.current = [ i for i in range(len(colours)) ]
            self.Vinit = [ math.asin(c.V) for c in colours ]
            for i, c in enumerate(colours):
                c.H = self.hues[i % len(self.hues)]
        self.nsteps += 1
        for c, V in zip(colours, self.Vinit):
            newV = self.minV + self.Vrange * \
                (1 + math.sin(V + self.dV * self.nsteps)) / 2.0
            # case where we switch to the next colour
            if newV > c.V and self.switched == False:
                self.current = [ i + 1 for i in self.current ]
                for i, c in enumerate(colours):
                    c.H = self.hues[self.current[i] % len(self.hues)]
                self.switched = True
            elif newV < c.V and self.switched == True:
                self.switched = False
            c.V = newV

    def reset(self):
        self.steps = 0

# Similar to ChristmasEffect but with random hues
class ChristmasEffectR(Effect):
    def __init__(self, V=0.1, minV=1/255, maxV=0.7):
        self.dV = V
        self.minV, self.maxV, self.Vrange = minV, maxV, maxV - minV
        self.V, self.Vinit = maxV, maxV
        self.nsteps = 0
        self.switched = False

    def setrandomhues(self, colours):
        dist = 1 / len(colours)
        H = random.random()
        for i, c in enumerate(colours):
            c.H = (H + dist * i) % 1
            
    def step(self, colours):
        if self.nsteps == 0:
            for i, c in enumerate(colours):
                c.V = self.Vinit
            self.setrandomhues(colours)
        #
        self.nsteps += 1
        newV = self.minV + self.Vrange * \
            (1 + math.sin(self.Vinit + self.dV * self.nsteps)) / 2.0
        # case where we switch to the next colour
        if newV > self.V and self.switched == False:
            self.setrandomhues(colours)
            self.switched = True
        elif newV < self.V and self.switched == True:
            self.switched = False
        self.V = newV
        for c in colours:
            c.V = self.V


# More Chistmassy stuff: fde different colours in and out asynchronously
class ChristmasEffectRA(Effect):
    def __init__(self, V=0.1, minV=1/255, maxV=0.7, stepamp=0.3):
        self.dV = V
        self.minV, self.maxV, self.Vrange = minV, maxV, maxV - minV
        self.nsteps = 0
        self.switched = False
        self.stepamp = stepamp

    def genstepsize(self):
        return 1 - self.stepamp + random.random() * (2 * self.stepamp)
    
    def step(self, colours):
        if self.nsteps == 0:
            self.Vinit = [ self.minV + random.random() * (self.maxV - self.minV)
                           for c in colours ]
            self.switched = [ False for c in colours ]
            self.stepsize = [ self.genstepsize() for i in colours ]
        #
        self.nsteps += 1
        for i, (c, V, s) in enumerate(zip(colours, self.Vinit, self.stepsize)):
            newV = self.minV + self.Vrange * \
                (1 + math.sin(V + self.dV * self.nsteps * s)) / 2.0
            # case where we switch to the next colour
            if newV > c.V and self.switched[i] == False:
                c.H = random.random()
                self.switched[i] = True
            elif newV < c.V and self.switched[i] == True:
                self.switched[i] = False
            c.V = newV
            
# Reset colours
class SpreadResetEffect(Effect):
    def step(self, colours):
        distance = 1/len(colours)
        rcs = generateSpreadColours(len(devices), distance=distance)
        colours[0].H, colours[0].S, colours[0].V = rcs[0].H, rcs[0].S, rcs[0].V
        for col1, col2 in zip(colours[0:-1], colours[1:]):
            col2.H, col2.S, col2.V = (col1.H + distance) % 1, col1.S, col1.V
            
# funstuff = list of (effect, number of steps, delay between steps) tuples
def fun(devices, colours, funstuff):
    # set initial colours
    for d, c in zip(devices, colours):
        setcolour(d, c.getRGBAColour())
    # now we just apply the effects in an endless loop
    while True:
        print('starting cycle!!')
        # apply each effect for the specified number of steps
        for effect, nsteps, delay in funstuff:
            for s in range(nsteps):
                effect.step(colours)
                for d, c in zip(devices, colours):
                    setcolour(d, c.getRGBAColour())
                time.sleep(delay)
            effect.reset()
        
if __name__ == '__main__':
    devices = finddevices()
    # list of HSV colours representing the current colour of each device
    colours = generateSpreadColours(len(devices), distance=.1)
    colours = generateSpreadColours(len(devices), distance=1/len(devices))
    effect1 = HSVCycleEffect(0.005, 0.0, 0.0)
    effect2 = HSVCycleEffect(0.00, 0.0, 0.05, minV=0.01)
    effect3 = HSVCycleEffect(0.00, 0.2, 0, minS=0.8)
    funstuff = [ #(ProgressiveResetEffect(), 1, 0),
                 # (RandomEffect(), 220, 1/100.),
                 # (effect2, 220, 1/30.),
                 # (effect3, 220, 1/30.),
        
                 (effect1, 500, 1/30.),
                 (ChristmasEffect(), 500, 1/30.),
                 (ChristmasEffectR(), 500, 1/30.),
                 (ChristmasEffectRA(), 500, 1/30.),
                 # (CombinedEffects([effect1, effect2, effect3]), 200, 1/30.),
                ]
    fun(devices, colours, funstuff)
