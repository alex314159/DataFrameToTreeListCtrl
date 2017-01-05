import  wx
import  wx.gizmos as gizmos
from wx.lib.pubsub import pub
import pandas

class DataFrameToTreeListCtrl(wx.Panel):
    """Class to define the Risk Tree Panel 

    Attributes:

    Methods:
    __init__()
    OnActivate()
    onCollapseAll()
    onRiskTreeQuery()
    OnRightUp()
    OnSize()
    onFillEODPrices()
    onUpdateTree()
    takeScreenshot()

    """
    def __init__(self, parent, df, groupList, treeHeader, treeHeaderWidth, columnHeaders, columnList, columnWidths, columnAlignment, columnFormats, strTreeID):
        """Keyword arguments:
        parent : parent 
        th = trade history (defaults to empty array if not specified)
        #groupedData in a multiindex Dataframe, typically the result of a df.groupby[columnList].sum()
        """
        wx.Panel.__init__(self, parent, wx.ID_ANY)#-1
        self.parent=parent
        self.df = df
        self.groupList = groupList
        self.treeHeader = treeHeader
        self.treeHeaderWidth = treeHeaderWidth
        self.columnHeaders = columnHeaders
        self.columnList = columnList
        self.columnWidths = columnWidths
        self.columnAlignment = columnAlignment
        self.columnFormats = columnFormats
        self.strTreeID = strTreeID
        self.groupedData = df.groupby(self.groupList)
        self.groupedDataSum = self.groupedData[columnList].sum()
        self.tree = gizmos.TreeListCtrl(self, wx.ID_ANY)
        isz = (16,16)
        il = wx.ImageList(isz[0], isz[1])
        self.fldridx     = il.Add(wx.ArtProvider_GetBitmap(wx.ART_FOLDER,      wx.ART_OTHER, isz))
        self.fldropenidx = il.Add(wx.ArtProvider_GetBitmap(wx.ART_FILE_OPEN,   wx.ART_OTHER, isz))
        self.fileidx     = il.Add(wx.ArtProvider_GetBitmap(wx.ART_NORMAL_FILE, wx.ART_OTHER, isz))
        self.il = il
        self.tree.SetImageList(il)
        # create some columns
        self.tree.AddColumn(self.treeHeader)
        self.tree.SetColumnAlignment(0,wx.ALIGN_LEFT)
        self.tree.SetColumnWidth(0,self.treeHeaderWidth)
        for i, (c,w,a) in enumerate(zip(columnHeaders,columnWidths,columnAlignment)):
            self.tree.AddColumn(c)
            self.tree.SetColumnAlignment(i+1,a)
            self.tree.SetColumnWidth(i+1,w)
        self.tree.SetMainColumn(0)
        #Bind events
        self.tree.GetMainWindow().Bind(wx.EVT_RIGHT_UP, self.onRightUp)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.tree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.onActivate)
        pub.subscribe(self.onUpdateTree, "REDRAW_TREE")
        #First draw
        self.onUpdateTree(MessageContainer('empty'))

    def onActivate(self,evt):
        self.active_path = []
        item = self.tree.GetSelection()
        while self.tree.GetItemParent(item):
            label = self.tree.GetItemText(item)
            self.active_path.insert(0, label)
            item = self.tree.GetItemParent(item)
        print self.active_path

    def onCollapseAll(self):
        self.recursiveCollapse(self.tree.GetRootItem())

    def recursiveCollapse(self, item):
        self.tree.Collapse(item)
        (child, cookie) = self.tree.GetFirstChild(item)
        while child.IsOk():
            self.recursiveCollapse(child)
            (child, cookie) = self.tree.GetNextChild(item, cookie)

    def onQuery(self, itemText):
        self.search_path_list = []
        self.recursiveSearch(self.tree.GetRootItem(), itemText, [])
        pass

    def recursiveSearch(self, item, itemText, path_to_here):
        text = self.tree.GetItemText(item)
        res = list(path_to_here)
        res.append(text)
        if text == itemText:
            self.search_path_list.append(res)
        else:
            (child, cookie) = self.tree.GetFirstChild(item)
            while child.IsOk():
                self.recursiveSearch(child,itemText,res)
                (child, cookie) = self.tree.GetNextChild(item, cookie)

    def onExpand(self, pathList):
        for p in pathList:
            self.recursiveExpand(self.tree.GetRootItem(),p)
            pass
        pass

    def recursiveExpand(self, item, remaining_path):
        text = self.tree.GetItemText(item)
        if text == remaining_path[0]:
            self.tree.Expand(item)
            if len(remaining_path)>1:
                (child, cookie) = self.tree.GetFirstChild(item)
                while child.IsOk():
                    self.recursiveExpand(child,remaining_path[1:])
                    (child, cookie) = self.tree.GetNextChild(item, cookie)

    def onRightUp(self, evt):
        pos = evt.GetPosition()
        item, flags, col = self.tree.HitTest(pos)
        if item:
            x=('Flags: %s, Col:%s, Text: %s' % (flags, col, self.tree.GetItemText(item, col)))
            print x

    def OnSize(self, evt):
        self.tree.SetSize(self.GetSize())

    def onUpdateTree(self, message):
        '''Event listener for the REDRAW_RISK_TREE event.
        '''
        self.groupedData = self.df.groupby(self.groupList)
        self.groupedDataSum = self.groupedData[self.columnList].sum()
        wx.CallAfter(self.drawTree)

    def drawLeaf(self, lvl, parent, parentItemList):
        if lvl == 0:
            generator = self.groupedDataSum.index.get_level_values(0).unique()
        else:
            generator = self.groupedDataSum.loc[tuple(parentItemList)].index.get_level_values(0).unique()
        for item in generator:
                child = self.tree.AppendItem(parent,item)
                itemList = list(parentItemList)
                itemList.append(item)
                if lvl < self.groupedDataSum.index.nlevels - 1:
                    self.tree.SetItemImage(child, self.fldridx, which = wx.TreeItemIcon_Normal)
                    self.tree.SetItemImage(child, self.fldropenidx, which = wx.TreeItemIcon_Expanded)
                else:
                    self.tree.SetItemImage(child, self.fileidx, which = wx.TreeItemIcon_Normal)
                for i, (c,f) in enumerate(zip(self.columnList,self.columnFormats)):
                    self.tree.SetItemText(child, f.format(self.groupedDataSum.loc[tuple(itemList)][c].sum()), i+1)
                if lvl < self.groupedDataSum.index.nlevels - 1:
                    self.drawLeaf(lvl+1, child, itemList)

    def drawTree(self):
        self.tree.Freeze()
        self.tree.DeleteAllItems()
        self.root = self.tree.AddRoot("Total")
        for i,(c,f) in enumerate(zip(self.columnList,self.columnFormats)):
            self.tree.SetItemText(self.root, f.format(self.groupedDataSum[c].sum()), i+1)
        self.drawLeaf(0,self.root,[])
        self.tree.Expand(self.root)
        self.tree.Thaw()
        pub.sendMessage('TREE_REDRAWN', message=MessageContainer(self.strTreeID))
        #self.onCollapseAll()
