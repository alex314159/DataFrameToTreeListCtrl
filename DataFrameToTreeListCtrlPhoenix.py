import pandas
import wx
import  wx.gizmos as gizmos
from pubsub import pub

class MessageContainer():
    def __init__(self,data):
        self.data = data

class DataFrameToTreeListCtrl(wx.Panel):
    """
    """

    def __init__(self, parent, df, groupList, treeHeader, treeHeaderWidth, columnHeaders, columnList, columnWidths,
                 columnAlignment, columnFormats, strTreeID):
        """Keyword arguments:
        parent : parent 
        groupedData in a multiindex Dataframe, typically the result of a df.groupby[columnList].sum()
        Note all columns must be different
        """
        wx.Panel.__init__(self, parent, wx.ID_ANY)  # -1
        self.parent = parent
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
        self.tree = gizmos.TreeListCtrl(self, wx.ID_ANY)
        isz = (16, 16)
        il = wx.ImageList(isz[0], isz[1])
        self.fldridx = il.Add(wx.ArtProvider.GetBitmap(wx.ART_FOLDER, wx.ART_OTHER, isz))
        self.fldropenidx = il.Add(wx.ArtProvider.GetBitmap(wx.ART_FILE_OPEN, wx.ART_OTHER, isz))
        self.fileidx = il.Add(wx.ArtProvider.GetBitmap(wx.ART_NORMAL_FILE, wx.ART_OTHER, isz))
        self.il = il
        self.tree.SetImageList(il)
        # create some columns
        self.tree.AddColumn(self.treeHeader)
        self.tree.SetColumnAlignment(0, wx.ALIGN_LEFT)
        self.tree.SetColumnWidth(0, self.treeHeaderWidth)
        for i, (c, w, a) in enumerate(zip(columnHeaders, columnWidths, columnAlignment)):
            self.tree.AddColumn(c)
            self.tree.SetColumnAlignment(i + 1, a)
            self.tree.SetColumnWidth(i + 1, w)
        self.tree.SetMainColumn(0)
        # Bind events
        self.tree.GetMainWindow().Bind(wx.EVT_RIGHT_UP, self.onRightUp)
        self.Bind(wx.EVT_SIZE, self.onSize)
        self.tree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.onActivate)
        pub.subscribe(self.onUpdateTree, "REDRAW_TREE")
        # First draw
        self.onUpdateTree(MessageContainer('empty'))

    def onActivate(self, evt):
        self.active_path = []
        item = self.tree.GetSelection()
        while self.tree.GetItemParent(item):
            label = self.tree.GetItemText(item)
            self.active_path.insert(0, label)
            item = self.tree.GetItemParent(item)
        print(self.active_path)

    def onCollapseAll(self):
        self.recursiveCollapse(self.tree.GetRootItem())

    def recursiveCollapse(self, item):
        self.tree.Collapse(item)
        (child, cookie) = self.tree.GetFirstChild(item)
        while child is not None and child.IsOk():
            self.recursiveCollapse(child)
            (child, cookie) = self.tree.GetNextChild(item, cookie)

    def onQuery(self, itemText):
        self.search_path_list = []
        self.recursiveSearch(self.tree.GetRootItem(), itemText, [])

    def recursiveSearch(self, item, itemText, path_to_here):
        text = self.tree.GetItemText(item)
        res = list(path_to_here)
        res.append(text)
        if text.upper() == itemText:
            self.search_path_list.append(res)
            return False
        else:
            loop = True
            (child, cookie) = self.tree.GetFirstChild(item)
            while child is not None and child.IsOk() and loop:
                loop = self.recursiveSearch(child, itemText, res)
                (child, cookie) = self.tree.GetNextChild(item, cookie)
            return loop

    def onExpand(self, pathList):
        for p in pathList:
            self.recursiveExpand(self.tree.GetRootItem(), p)

    def recursiveExpand(self, item, remaining_path):
        text = self.tree.GetItemText(item)
        if text == remaining_path[0]:
            self.tree.Expand(item)
            if len(remaining_path) > 1:
                (child, cookie) = self.tree.GetFirstChild(item)
                while child is not None and child.IsOk():
                    self.recursiveExpand(child, remaining_path[1:])
                    (child, cookie) = self.tree.GetNextChild(item, cookie)

    def onRightUp(self, evt):
        pos = evt.GetPosition()
        item, flags, col = self.tree.HitTest(pos)
        if item:
            x = ('Flags: %s, Col:%s, Text: %s' % (flags, col, self.tree.GetItemText(item, col)))
            print(x)

    def onSize(self, evt):
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
            child = self.tree.AppendItem(parent, item)
            itemList = list(parentItemList)
            itemList.append(item)
            if lvl < self.groupedDataSum.index.nlevels - 1:
                self.tree.SetItemImage(child, self.fldridx, which=wx.TreeItemIcon_Normal)
                self.tree.SetItemImage(child, self.fldropenidx, which=wx.TreeItemIcon_Expanded)
            else:
                self.tree.SetItemImage(child, self.fileidx, which=wx.TreeItemIcon_Normal)
            if lvl < self.groupedDataSum.index.nlevels - 1:
                summed = self.groupedDataSum.loc[tuple(itemList)].sum()  # this accelerates
                for i, (c, f) in enumerate(zip(self.columnList, self.columnFormats)):
                    self.tree.SetItemText(child, f.format(summed[c]), i + 1)
                self.drawLeaf(lvl + 1, child, itemList)  # recursion
            else:
                for i, (c, f) in enumerate(zip(self.columnList, self.columnFormats)):
                    self.tree.SetItemText(child, f.format(self.groupedDataSum.loc[tuple(itemList)][c].sum()), i + 1)

    def drawTree(self):
        self.tree.Freeze()
        self.tree.DeleteAllItems()
        self.root = self.tree.AddRoot("Total")
        for i, (c, f) in enumerate(zip(self.columnList, self.columnFormats)):
            self.tree.SetItemText(self.root, f.format(self.groupedDataSum[c].sum()), i + 1)
        self.drawLeaf(0, self.root, [])
        self.tree.Expand(self.root)
        self.tree.Thaw()
        pub.sendMessage('TREE_REDRAWN', message=MessageContainer(self.strTreeID))

    def expand_first_level(self):
        (child, cookie) = self.tree.GetFirstChild(self.root)
        while child is not None and child.IsOk():
            self.tree.Expand(child)
            (child, cookie) = self.tree.GetNextChild(self.root, cookie)


class TreeTest(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self,None, wx.ID_ANY, "Tree test",size=(925,850))
        dc = {'Customer': {0: 'a', 1: 'b', 2: 'c', 3: 'd', 4: 'e', 5: 'f', 6: 'g', 7: 'h', 8: 'i', \
                           9: 'j', 10: 'k', 11: 'l', 12: 'm', 13: 'n', 14: 'o', 15: 'p'}, \
              'February': {0: 50, 1: 48, 2: 46, 3: 44, 4: 42, 5: 40, 6: 38, 7: 36, 8: 34, 9: 32, \
                           10: 30, 11: 28, 12: 26, 13: 24, 14: 22, 15: 20}, \
              'January': {0: 1, 1: 3, 2: 5, 3: 7, 4: 9, 5: 11, 6: 13, 7: 15, 8: 17, 9: 19, 10: 21, \
                          11: 23, 12: 25, 13: 27, 14: 29, 15: 31}, \
              'Region': {0: 'America', 1: 'Asia', 2: 'Europe', 3: 'Africa', 4: 'America', 5: 'Asia', \
                         6: 'Europe', 7: 'Africa', 8: 'America', 9: 'Asia', 10: 'Europe', 11: 'Africa', \
                         12: 'America', 13: 'Asia', 14: 'Europe', 15: 'Africa'}, \
              'Salesperson': {0: 'John', 1: 'Mary', 2: 'John', 3: 'Mary', 4: 'John', 5: 'Mary', \
                              6: 'John', 7: 'Mary', 8: 'John', 9: 'Mary', 10: 'John', 11: 'Mary', \
                              12: 'John', 13: 'Mary', 14: 'John', 15: 'Mary'}}
        df = pandas.DataFrame(dc)
        groupList = ['Salesperson','Region']
        treeHeader = 'Key'
        treeHeaderWidth = 200
        columnHeaders = ['Jan','Feb']
        columnList = ['January','February']
        columnWidths = [100,200]
        columnAlignment = [wx.ALIGN_RIGHT,wx.ALIGN_RIGHT]
        columnFormats = ['{:,.0f}','{:,.0f}']
        tree = DataFrameToTreeListCtrl(self, df, groupList, treeHeader, treeHeaderWidth, columnHeaders, columnList, columnWidths, columnAlignment, columnFormats, 'TEST_TREE')
        box = wx.BoxSizer(wx.VERTICAL)
        box.Add(tree, 1, wx.EXPAND)
        self.SetAutoLayout(True)
        self.SetSizer(box)
        self.Layout()


if __name__ == "__main__":
    app = wx.App()
    frame = TreeTest().Show()
    app.MainLoop()
