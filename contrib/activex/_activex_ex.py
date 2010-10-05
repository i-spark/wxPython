

#---------------------------------------------------------------------------
# Some helper and utility functions for ActiveX


t4 = " " * 4
t8 = " " * 8

def GetAXInfo(ax):
    """
    Returns a printable summary of the TypeInfo from the ActiveX instance
    passed in.
    """

    def ProcessFuncX(f, out, name):
        out.append(name)
        out.append(t4 + "retType:  %s" % f.retType.vt_type)
        if f.params:
            out.append(t4 + "params:")
            for p in f.params:
                out.append(t8 + p.name)
                out.append(t8+t4+ "in:%s  out:%s  optional:%s  type:%s" % (p.isIn, p.isOut, p.isOptional, p.vt_type))
        out.append('')

    def ProcessPropX(p, out):
        out.append(GernerateAXModule.trimPropName(p.name))
        out.append(t4+ "type:%s  arg:%s  canGet:%s  canSet:%s" % (p.type.vt_type, p.arg.vt_type, p.canGet, p.canSet))
        out.append('')

    out = []

    out.append("PROPERTIES")
    out.append("-"*20)
    for p in ax.GetAXProperties():
        ProcessPropX(p, out)
    out.append('\n\n')

    out.append("METHODS")
    out.append("-"*20)
    for m in ax.GetAXMethods():
        ProcessFuncX(m, out, GernerateAXModule.trimMethodName(m.name))
    out.append('\n\n')

    out.append("EVENTS")
    out.append("-"*20)
    for e in ax.GetAXEvents():
        ProcessFuncX(e, out, GernerateAXModule.trimEventName(e.name))
    out.append('\n\n')

    return "\n".join(out)



class GernerateAXModule:
    def __init__(self, ax, className, modulePath, moduleName=None, verbose=False):
        """
        Make a Python module file with a class that has been specialized
        for the AcitveX object.

            ax           An instance of the ActiveXWindow class
            className    The name to use for the new class
            modulePath   The path where the new module should be written to
            moduleName   The name of the .py file to create.  If not given
                         then the className will be used.
        """
        import os
        if moduleName is None:
            moduleName = className + '.py'
        filename = os.path.join(modulePath, moduleName)
        if verbose:
            print "Creating module in:", filename
            print "  ProgID:  ", ax.GetCLSID().GetProgIDString()
            print "  CLSID:   ", ax.GetCLSID().GetCLSIDString()
            print
        self.mf = file(filename, "w")
        self.WriteFileHeader(ax)
        self.WriteEvents(ax)
        self.WriteClassHeader(ax, className)
        self.WriteMethods(ax)
        self.WriteProperties(ax)
        self.WriteDocs(ax)
        self.mf.close()
        del self.mf


    def WriteFileHeader(self, ax):
        self.write("# This module was generated by the wx.activex.GernerateAXModule class\n"
                   "# (See also the genaxmodule script.)\n")
        self.write("import wx")
        self.write("import wx.activex\n")
        self.write("clsID = '%s'\nprogID = '%s'\n"
                   % (ax.GetCLSID().GetCLSIDString(), ax.GetCLSID().GetProgIDString()))
        self.write("\n")


    def WriteEvents(self, ax):
        events = ax.GetAXEvents()
        if events:
            self.write("# Create eventTypes and event binders")
            for e in events:
                self.write("wxEVT_%s = wx.activex.RegisterActiveXEvent('%s')"
                           % (self.trimEventName(e.name), e.name))
            self.write()
            for e in events:
                n = self.trimEventName(e.name)
                self.write("EVT_%s = wx.PyEventBinder(wxEVT_%s, 1)" % (n,n))
            self.write("\n")


    def WriteClassHeader(self, ax, className):
        self.write("# Derive a new class from ActiveXWindow")
        self.write("""\
class %s(wx.activex.ActiveXWindow):
    def __init__(self, parent, ID=-1, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=0, name='%s'):
        wx.activex.ActiveXWindow.__init__(self, parent,
            wx.activex.CLSID('%s'),
            ID, pos, size, style, name)
        """ % (className, className, ax.GetCLSID().GetCLSIDString()) )


    def WriteMethods(self, ax):
        methods = ax.GetAXMethods()
        if methods:
            self.write(t4, "# Methods exported by the ActiveX object")
            for m in methods:
                name = self.trimMethodName(m.name)
                self.write(t4, "def %s(self%s):" % (name, self.getParameters(m, True)))
                self.write(t8, "return self.CallAXMethod('%s'%s)" % (m.name, self.getParameters(m, False)))
                self.write()
            

    def WriteProperties(self, ax):
        props = ax.GetAXProperties()
        if props:
            self.write(t4, "# Getters, Setters and properties")
            for p in props:
                getterName = setterName = "None"
                if p.canGet:
                    getterName = "_get_" + p.name
                    self.write(t4, "def %s(self):" % getterName)
                    self.write(t8, "return self.GetAXProp('%s')" % p.name)
                if p.canSet:
                    setterName = "_set_" + p.name
                    self.write(t4, "def %s(self, %s):" % (setterName, p.arg.name))
                    self.write(t8, "self.SetAXProp('%s', %s)" % (p.name, p.arg.name))

                self.write(t4, "%s = property(%s, %s)" %
                           (self.trimPropName(p.name), getterName, setterName))
                self.write()
                

    def WriteDocs(self, ax):
        self.write()
        doc = GetAXInfo(ax)
        for line in doc.split('\n'):
            self.write("#  ", line)
            


    def write(self, *args):
        for a in args:
            self.mf.write(a)
        self.mf.write("\n")


    def trimEventName(name):
        if name.startswith("On"):
            name = name[2:]
        return name
    trimEventName = staticmethod(trimEventName)


    def trimPropName(name):
        #name = name[0].lower() + name[1:]
        name = name.lower()
        import keyword
        if name in keyword.kwlist: name += '_'
        return name
    trimPropName = staticmethod(trimPropName)


    def trimMethodName(name):
        import keyword
        if name in keyword.kwlist: name += '_'
        return name
    trimMethodName = staticmethod(trimMethodName)
    

    def getParameters(self, m, withDefaults):
        import keyword
        st = ""
        # collect the input parameters, if both isIn and isOut are
        # False then assume it is an input paramater
        params = []
        for p in m.params:
            if p.isIn or (not p.isIn and not p.isOut):
                params.append(p)
        # did we get any?
        for p in params:
            name = p.name
            if name in keyword.kwlist: name += '_'
            st += ", "
            st += name
            if withDefaults and p.isOptional:
                st += '=None'
        return st


#---------------------------------------------------------------------------