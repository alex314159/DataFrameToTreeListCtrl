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
                 columnAlignment, columnFormats, strTreeID, firstDraw=True, updateString='REDRAW_TREE'):
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
        pub.subscribe(self.onUpdateTree, updateString)
        if firstDraw:
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




class DataFrameToTreeListCtrlLazy(wx.Panel):
    """
    """

    def __init__(self, parent, df, groupList, treeHeader, treeHeaderWidth, columnHeaders, columnList, columnWidths,
                 columnAlignment, columnFormats, strTreeID, firstDraw=True, updateString='REDRAW_TREE'):
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
        self.root = None
        self.groupedData = None
        self.groupedDataSum = None
        self.all_paths = None
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
        self.tree.Bind(wx.EVT_TREE_ITEM_EXPANDING, self.expand_and_draw)
        pub.subscribe(self.update_tree, updateString)
        self.expanded_items = {}
        if firstDraw:
            self.update_tree(MessageContainer('empty'))


    def onActivate(self, evt):
        self.active_path = []
        item = self.tree.GetSelection()
        while self.tree.GetItemParent(item):
            label = self.tree.GetItemText(item)
            self.active_path.insert(0, label)
            item = self.tree.GetItemParent(item)
        print(self.active_path)

    def collapse_all(self):
        self.recursive_collapse(self.tree.GetRootItem())
        self.root.Expand()

    def recursive_collapse(self, item):
        self.tree.Collapse(item)
        (child, cookie) = self.tree.GetFirstChild(item)
        while child is not None and child.IsOk():
            self.recursive_collapse(child)
            (child, cookie) = self.tree.GetNextChild(item, cookie)

    def search(self, item_text):
        self.root.Expand()
        res = [p for p in self.all_paths if item_text.upper() in [a.upper() for a in p]]
        for p in res:
            self.recursive_search_expand(self.root, p)

    def recursive_search_expand(self, item, p):
        (child, cookie) = self.tree.GetFirstChild(item)
        while child is not None and child.IsOk():
            if self.tree.GetItemText(child) == p[0]:
                self.tree.Expand(child)
                self.recursive_search_expand(child, p[1:])
            (child, cookie) = self.tree.GetNextChild(item, cookie)

    def expand_and_draw(self, event):
        item = event.GetItem()
        try:
            ok = self.expanded_items[item]
        except (IndexError, KeyError):
            self.expanded_items[item] = True
            self.tree.DeleteChildren(item)
            lvl = 0
            item_list = [self.tree.GetItemText(item)]
            item_rec = item
            while self.tree.GetItemParent(item_rec):
                item_rec = self.tree.GetItemParent(item_rec)
                item_list.append(self.tree.GetItemText(item_rec))
                lvl = lvl + 1
            item_list.reverse()
            item_list_tuple = tuple(item_list[1:])
            self.draw_leaf(lvl, item, item_list_tuple, lvl + 1)

    def onRightUp(self, evt):
        pos = evt.GetPosition()
        item, flags, col = self.tree.HitTest(pos)
        if item:
            x = ('Flags: %s, Col:%s, Text: %s' % (flags, col, self.tree.GetItemText(item, col)))
            print(x)

    def onSize(self, evt):
        self.tree.SetSize(self.GetSize())

    def update_tree(self, message):
        '''Event listener for the REDRAW_RISK_TREE event.
        '''
        self.groupedData = self.df.groupby(self.groupList)
        self.groupedDataSum = self.groupedData[self.columnList].sum()
        self.all_paths = list(self.groupedData.indices)
        wx.CallAfter(self.draw_tree)

    def draw_leaf(self, lvl, parent, parentItemList, max_level):
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
                if lvl < max_level - 1:
                    self.draw_leaf(lvl + 1, child, itemList, max_level)  # recursion
                else:
                    self.tree.AppendItem(child, 'dummy_tree_entry')
            else:
                for i, (c, f) in enumerate(zip(self.columnList, self.columnFormats)):
                    self.tree.SetItemText(child, f.format(self.groupedDataSum.loc[tuple(itemList)][c].sum()), i + 1)

    def draw_tree(self):
        self.tree.Freeze()
        self.tree.DeleteAllItems()
        self.expanded_items = {}
        self.root = self.tree.AddRoot("Total")
        for i, (c, f) in enumerate(zip(self.columnList, self.columnFormats)):
            self.tree.SetItemText(self.root, f.format(self.groupedDataSum[c].sum()), i + 1)
        self.draw_leaf(0, self.root, [], 1)
        self.expanded_items[self.root] = True
        self.tree.Expand(self.root)
        self.tree.Thaw()
        pub.sendMessage('TREE_REDRAWN', message=MessageContainer(self.strTreeID))

    def expand_first_level(self):
        (child, cookie) = self.tree.GetFirstChild(self.root)
        while child is not None and child.IsOk():
            self.tree.Expand(child)
            (child, cookie) = self.tree.GetNextChild(self.root, cookie)

    def recursive_expand(self, item):
        self.tree.Expand(item)
        (child, cookie) = self.tree.GetFirstChild(item)
        while child is not None and child.IsOk():
            self.recursive_expand(child)
            (child, cookie) = self.tree.GetNextChild(item, cookie)

    def to_excel(self, path):
        self.groupedDataSum.to_excel(path)


class TreeTest(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self,None, wx.ID_ANY, "Tree test",size=(925, 850))
        dc = {
            'Customer': {
                0: 'a', 1: 'b', 2: 'c', 3: 'd', 4: 'e',
                5: 'f', 6: 'g', 7: 'h', 8: 'i',
                9: 'j', 10: 'k', 11: 'l', 12: 'm',
                13: 'n', 14: 'o', 15: 'p', 16: 'a',
                17: 'b', 18: 'c', 19: 'd', 20: 'e',
                21: 'f', 22: 'g', 23: 'h', 24: 'i',
                25: 'j', 26: 'k', 27: 'l', 28: 'm',
                29: 'n', 30: 'o', 31: 'p'},
            'February': {
                0: 50,
                1: 48, 2: 46, 3: 44, 4: 42, 5: 40,
                6: 38, 7: 36, 8: 34, 9: 32, 10: 30,
                11: 28, 12: 26, 13: 24, 14: 22,
                15: 20, 16: 37, 17: 28, 18: 12,
                19: 28, 20: 23, 21: 13, 22: 12,
                23: 20, 24: 17, 25: 27, 26: 25,
                27: 17, 28: 25, 29: 15, 30: 15,
                31: 27},
            'January': {
                0: 1, 1: 3, 2: 5, 3: 7,
                4: 9, 5: 11, 6: 13, 7: 15, 8: 17,
                9: 19, 10: 21, 11: 23, 12: 25,
                13: 27, 14: 29, 15: 31, 16: 11, 17: 30,
                18: 24, 19: 36, 20: 29, 21: 11, 22: 24,
                23: 18, 24: 33, 25: 35, 26: 30, 27: 19,
                28: 34, 29: 33, 30: 39, 31: 11},
            'Region': {
                0: 'America', 1: 'Asia', 2: 'Europe', 3: 'Africa', 4: 'America',
                5: 'Asia', 6: 'Europe', 7: 'America', 8: 'America',
                9: 'Asia', 10: 'Europe', 11: 'Africa', 12: 'America',
                13: 'Asia', 14: 'Europe', 15: 'Africa', 16: 'Asia',
                17: 'Europe', 18: 'Africa', 19: 'America', 20: 'Asia',
                21: 'Europe', 22: 'America', 23: 'America', 24: 'Asia',
                25: 'Europe', 26: 'Africa', 27: 'America', 28: 'Asia',
                29: 'Europe', 30: 'Africa', 31: 'Africa'},
            'Salesperson': {
                0: 'John', 1: 'Mary', 2: 'John',
                3: 'Mary', 4: 'John', 5: 'Mary', 6: 'John',
                7: 'Mary', 8: 'John', 9: 'Mary', 10: 'John',
                11: 'Mary', 12: 'John', 13: 'Mary',
                14: 'John', 15: 'Mary', 16: 'John',
                17: 'Mary', 18: 'John', 19: 'Mary', 20: 'John',
                21: 'Mary', 22: 'John', 23: 'Mary', 24: 'John',
                25: 'Mary', 26: 'John', 27: 'Mary',
                28: 'John', 29: 'Mary', 30: 'John', 31: 'Mary'}}

        df = pandas.DataFrame(dc)
        groupList = ['Salesperson', 'Region', 'Customer']
        treeHeader = 'Key'
        treeHeaderWidth = 200
        columnHeaders = ['Jan', 'Feb']
        columnList = ['January', 'February']
        columnWidths = [100,200]
        columnAlignment = [wx.ALIGN_RIGHT,wx.ALIGN_RIGHT]
        columnFormats = ['{:,.0f}', '{:,.0f}']
        self.tree = DataFrameToTreeListCtrlLazy(self, df, groupList, treeHeader, treeHeaderWidth, columnHeaders, columnList, columnWidths, columnAlignment, columnFormats, 'TEST_TREE')
        btn1 = wx.Button(self, label="Expand all")
        btn1.Bind(wx.EVT_BUTTON, self.btn1_action)
        btn2 = wx.Button(self, label="Collapse all")
        btn2.Bind(wx.EVT_BUTTON, self.btn2_action)
        btn4 = wx.Button(self, label="Search for America")
        btn4.Bind(wx.EVT_BUTTON, self.btn4_action)
        box = wx.BoxSizer(wx.VERTICAL)
        box.Add(btn1, 0, wx.EXPAND)
        box.Add(btn2, 0, wx.EXPAND)
        box.Add(btn4, 0, wx.EXPAND)
        box.Add(self.tree, 1, wx.EXPAND | wx.ALL, 20)
        self.SetAutoLayout(True)
        self.SetSizer(box)
        self.Layout()

    def btn1_action(self, event):

        self.tree.recursive_expand(self.tree.root)
        pass

    def btn2_action(self, event):
        self.tree.collapse_all()
        pass

    def btn4_action(self, event):
        self.tree.search('America')


if __name__ == "__main__":
    app = wx.App()
    frame = TreeTest().Show()
    app.MainLoop()
