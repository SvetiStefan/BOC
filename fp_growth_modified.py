# encoding: utf-8

"""
A Python implementation of the FP-growth algorithm.

Basic usage of the module is very simple:

    >>> from fp_growth import find_frequent_itemsets
    >>> find_frequent_itemsets(transactions, minimum_support)
"""

from collections import defaultdict, namedtuple
from itertools import imap
from scipy import stats
import numpy as np
import time


def find_frequent_itemsets(transactions, minimum_support, minimum_confidence, include_support_n_confidence=False):
    """
    Find frequent itemsets in the given transactions using FP-growth. This
    function returns a generator instead of an eagerly-populated list of items.

    The `transactions` parameter can be any iterable of iterables of items.
    `minimum_support` should be an integer specifying the minimum number of
    occurrences of an itemset for it to be accepted. `minimum_confidence` should
    be a float value between 0 and 1, indicating the minimum confidence of
    the output pattern.

    Each item must be hashable (i.e., it must be valid as a member of a
    dictionary or a set).

    If `include_support_n_confidence` is true, yield (itemset, support, pos_count, 
    confidence) instead of just the itemsets.
    """
    items = defaultdict(lambda: 0) # mapping from items to their supports
    processed_transactions = []
    positive_no = 0
    negative_no = 0

    # Labeled_Trans for transaction with labels
    Labeled_Trans = namedtuple('Labeled_Trans', 'trans label')

    # Load the passed-in transactions and count the support that individual
    # items have.
    for transaction in transactions:
        # Assert when transaction lenth <= 2 since a transaction with id and label should has at least lenth of 3
        assert len(transaction) > 2, "Transaction %s has no more than 2 items" % ','.join(transaction)
        # Remove id
        transaction.pop(0)
        # Get label
        label = True if transaction.pop(-1) == 'T' else False
        if label:
            positive_no += 1
        else:
            negative_no += 1
        processed = []
        for item in transaction:
            items[item] += 1
            processed.append(item)
        processed_transactions.append(Labeled_Trans(processed, label))

    # Remove infrequent items from the item support dictionary.
    items = dict((item, support) for item, support in items.iteritems()
        if support >= minimum_support)

    # This is to avoid that if two single items with the same support
    # the sort won't be able to affect their order
    res = list(sorted(items, key=items.__getitem__, reverse=True))
    order_items = dict((item, order) for item, order in zip(res, range(len(res))))

    # Build our FP-tree. Before any transactions can be added to the tree, they
    # must be stripped of infrequent items and their surviving items must be
    # sorted in decreasing order of frequency.
    def clean_transaction(transaction):
        cleaned_transaction = filter(lambda v: v in order_items, transaction.trans)
        cleaned_transaction.sort(key=lambda v: order_items[v], reverse=False)
        return Labeled_Trans(cleaned_transaction, transaction.label)

    master = FPTree()
    for transaction in imap(clean_transaction, processed_transactions):
        #print transaction.trans, transaction.label
        master.add(transaction.trans, 1, (1 if transaction.label else 0))

    def find_with_suffix(tree, suffix):
        if tree.no_branch:
            # Pruning: directly output in this case
            suffix_set = tree.item_order
            remaining_set = suffix_set
            last_support = 0
            for item in reversed(suffix_set):
                _nodes = list(tree.nodes(item))
                support, pos_count = sum(n.count for n in _nodes), sum(n.pos_count for n in _nodes)
                confidence = 0 if support == 0 else float(pos_count) / support
                chi_square = stats.chisquare(np.array([pos_count, support - pos_count]), np.array([positive_no, negative_no]))[0]
                if last_support != 0 and last_support == support:
                    continue
                if confidence >= minimum_confidence:
                    yield ((remaining_set + suffix), support, pos_count, confidence, chi_square) if include_support_n_confidence else remaining_set
                last_support = support
                remaining_set.pop(-1)
            return
        for item in reversed(tree.item_order):
            _nodes = list(tree.nodes(item))
            support, pos_count = sum(n.count for n in _nodes), sum(n.pos_count for n in _nodes)
            confidence = 0 if support == 0 else float(pos_count) / support
            chi_square = stats.chisquare(np.array([pos_count, support - pos_count]), np.array([positive_no, negative_no]))[0]
            if support >= minimum_support and item not in suffix:
                # Extend suffix
                suffix_set = [item] + suffix
                if confidence >= minimum_confidence:
                    # yield only when confidence >= minimum_confidence
                    yield (suffix_set, support, pos_count, confidence, chi_square) if include_support_n_confidence else suffix_set

                # Build a conditional tree and recursively search for frequent
                # itemsets within it.
                cond_tree = modified_conditional_tree_from_paths(tree.prefix_paths(item),
                    minimum_support)
                for s in find_with_suffix(cond_tree, suffix_set):
                    yield s # pass along the good news to our caller

    # Search for frequent itemsets, and yield the results we find.
    for itemset in find_with_suffix(master, []):
        yield itemset

class FPTree(object):
    """
    An FP tree.

    This object may only store transaction items that are hashable (i.e., all
    items must be valid as dictionary keys or set members).
    """

    Route = namedtuple('Route', 'head tail')

    def __init__(self):
        # The root node of the tree.
        self._root = FPNode(self, None, None, None)

        # A dictionary mapping items to the head and tail of a path of
        # "neighbors" that will hit every node containing that item.
        self._routes = {}
        self._no_branch = True
        # Use this to keep the order of items inserted into the tree.
        # The order in _routes is not reliable.
        self._item_order = []

    @property
    def root(self):
        """The root node of the tree."""
        return self._root

    def add(self, transaction, label):
        """
        Adds a transaction to the tree.
        """

        point = self._root

        for item in transaction:
            next_point = point.search(item)
            if next_point:
                # There is already a node in this tree for the current
                # transaction item; reuse it.
                next_point.increment(label)
            else:
                # Create a new point and add it as a child of the point we're
                # currently looking at.
                next_point = FPNode(self, item, 1, (1 if label else 0))
                point.add(next_point)
                if len(point._children) > 1:
                    self._no_branch = False
                # Update the route of nodes that contain this item to include
                # our new node.
                self._update_route(next_point)

            point = next_point

    def add(self, transaction, count, pos_count):
        """
        Adds a transaction to the tree, with count and pos_count.
        """

        point = self._root

        for item in transaction:
            next_point = point.search(item)
            if next_point:
                # There is already a node in this tree for the current
                # transaction item; reuse it.
                next_point.increment(count, pos_count)
            else:
                # Create a new point and add it as a child of the point we're
                # currently looking at.
                next_point = FPNode(self, item, count, pos_count)
                point.add(next_point)
                if len(point._children) > 1:
                    self._no_branch = False
                # Update the route of nodes that contain this item to include
                # our new node.
                self._update_route(next_point)

            point = next_point

    def _update_route(self, point):
        """Add the given node to the route through all nodes for its item."""
        assert self is point.tree

        try:
            route = self._routes[point.item]
            route[1].neighbor = point # route[1] is the tail
            self._routes[point.item] = self.Route(route[0], point)
        except KeyError:
            # First node for this item; start a new route.
            self._routes[point.item] = self.Route(point, point)
            self._item_order.append(point.item)

    def items(self):
        """
        Generate one 2-tuples for each item represented in the tree. The first
        element of the tuple is the item itself, and the second element is a
        generator that will yield the nodes in the tree that belong to the item.
        """
        for item in self._routes.iterkeys():
            yield (item, self.nodes(item))

    def nodes(self, item):
        """
        Generates the sequence of nodes that contain the given item.
        """

        try:
            node = self._routes[item][0]
        except KeyError:
            return

        while node:
            yield node
            node = node.neighbor

    def prefix_paths(self, item):
        """Generates the prefix paths that end with the given item."""

        def collect_path(node):
            path = []
            while node and not node.root:
                path.append(node)
                node = node.parent
            path.reverse()
            return path

        return (collect_path(node) for node in self.nodes(item))

    def inspect(self):
        print 'Tree:'
        self.root.inspect(1)

        print
        print 'Routes:'
        for item, nodes in self.items():
            print '  %r' % item
            for node in nodes:
                print '    %r' % node

    def _removed(self, node):
        """Called when `node` is removed from the tree; performs cleanup."""

        head, tail = self._routes[node.item]
        if node is head:
            if node is tail or not node.neighbor:
                # It was the sole node.
                del self._routes[node.item]
            else:
                self._routes[node.item] = self.Route(node.neighbor, tail)
                self._item_order = filter(lambda x: x != node.item, self._item_order)
        else:
            for n in self.nodes(node.item):
                if n.neighbor is node:
                    n.neighbor = node.neighbor # skip over
                    if node is tail:
                        self._routes[node.item] = self.Route(head, n)
                    break

    @property
    def no_branch(self):
        """Return if this tree has branches or not."""
        return self._no_branch

    @no_branch.setter
    def no_branch(self, value):
        """Set if this tree has branches or not."""
        self._no_branch = value

    @property
    def item_order(self):
        """Return _item_order"""
        return self._item_order

def modified_conditional_tree_from_paths(paths, minimum_support):
    """
    Modified version of conditional_tree_from_paths.
    Generally, when build a modified conditional tree, we should also
    sort all the nodes, remove nodes that does not meet the minimun
    support -- this will reduce the execution time and memory.
    """
    condition_item = None
    items = defaultdict(lambda: 0) # mapping from items to their supports
    processed_transactions = []

    # Stat_Trans for transaction with count and pos_count
    Stat_Trans = namedtuple('Labeled_Trans', 'trans stat')

    for path in paths:
        if condition_item is None:
            condition_item = path[-1].item
        count, pos_count = path[-1].count, path[-1].pos_count
        processed = []
        for node in path:
            items[node.item] += count
            processed.append(node.item)
        processed_transactions.append(Stat_Trans(processed, (count, pos_count)))

    items.pop(condition_item, None)
    items = dict((item, support) for item, support in items.iteritems() if support >= minimum_support)
    res = list(sorted(items, key=items.__getitem__, reverse=True))
    order_items = dict((item, order) for item, order in zip(res, range(len(res))))

    def clean_transaction(transaction):
        cleaned_transaction = filter(lambda v: v in order_items, transaction.trans)
        cleaned_transaction.sort(key=lambda v: order_items[v], reverse=False)
        return Stat_Trans(cleaned_transaction, transaction.stat)

    master = FPTree()
    for transaction in imap(clean_transaction, processed_transactions):
        master.add(transaction.trans, transaction.stat[0], transaction.stat[1])
    return master

def conditional_tree_from_paths(paths, minimum_support):
    """Builds a conditional FP-tree from the given prefix paths."""
    tree = FPTree()
    condition_item = None
    items = set()

    # Import the nodes in the paths into the new tree. Only the counts of the
    # leaf notes matter; the remaining counts will be reconstructed from the
    # leaf counts.
    for path in paths:
        if condition_item is None:
            condition_item = path[-1].item

        point = tree.root
        for node in path:
            next_point = point.search(node.item)
            if not next_point:
                # Add a new node to the tree.
                items.add(node.item)
                count = node.count if node.item == condition_item else 0
                pos_count = node.pos_count if node.item == condition_item else 0
                next_point = FPNode(tree, node.item, count, pos_count)
                point.add(next_point)
                if len(point.children) > 1:
                    tree.no_branch = False
                tree._update_route(next_point)
            point = next_point

    assert condition_item is not None

    # Calculate the counts of the non-leaf nodes.
    for path in tree.prefix_paths(condition_item):
        count = path[-1].count
        pos_count = path[-1].pos_count
        for node in reversed(path[:-1]):
            node._count += count
            node._pos_count += pos_count

    # Eliminate the nodes for any items that are no longer frequent.
    for item in items:
        support = sum(n.count for n in tree.nodes(item))
        if support < minimum_support:
            # Doesn't make the cut anymore
            for node in tree.nodes(item):
                if node.parent is not None:
                    node.parent.remove(node)

    # Finally, remove the nodes corresponding to the item for which this
    # conditional tree was generated.
    for node in tree.nodes(condition_item):
        if node.parent is not None: # the node might already be an orphan
            node.parent.remove(node)

    return tree

class FPNode(object):
    """A node in an FP tree."""

    def __init__(self, tree, item, count, pos_count):
        self._tree = tree
        self._item = item
        self._count = count
        self._pos_count = pos_count # _pos_count is the count in positive class
        self._parent = None
        self._children = {}
        self._neighbor = None

    def add(self, child):
        """Adds the given FPNode `child` as a child of this node."""

        if not isinstance(child, FPNode):
            raise TypeError("Can only add other FPNodes as children")

        if not child.item in self._children:
            self._children[child.item] = child
            child.parent = self

    def search(self, item):
        """
        Checks to see if this node contains a child node for the given item.
        If so, that node is returned; otherwise, `None` is returned.
        """

        try:
            return self._children[item]
        except KeyError:
            return None

    def remove(self, child):
        try:
            if self._children[child.item] is child:
                del self._children[child.item]
                child.parent = None
                self._tree._removed(child)
                for sub_child in child.children:
                    try:
                        # Merger case: we already have a child for that item, so
                        # add the sub-child's count to our child's count.
                        self._children[sub_child.item]._count += sub_child.count
                        sub_child.parent = None # it's an orphan now
                    except KeyError:
                        # Turns out we don't actually have a child, so just add
                        # the sub-child as our own child.
                        self.add(sub_child)
                child._children = {}
            else:
                raise ValueError("that node is not a child of this node")
        except KeyError:
            raise ValueError("that node is not a child of this node")

    def __contains__(self, item):
        return item in self._children

    @property
    def tree(self):
        """The tree in which this node appears."""
        return self._tree

    @property
    def item(self):
        """The item contained in this node."""
        return self._item

    @property
    def count(self):
        """The count associated with this node's item."""
        return self._count

    @property
    def pos_count(self):
        """The pos_count associated with this node's item."""
        return self._pos_count

    def increment(self, label):
        """Increments the count associated with this node's item."""
        if self._count is None or self._pos_count is None:
            raise ValueError("Root nodes have no associated count/pos_count.")
        self._count += 1
        if label:
            self._pos_count += 1

    def increment(self, count, pos_count):
        """Increments the count associated with this node's item."""
        if self._count is None or self._pos_count is None:
            raise ValueError("Root nodes have no associated count/pos_count.")
        self._count += count
        self._pos_count += pos_count


    @property
    def root(self):
        """True if this node is the root of a tree; false if otherwise."""
        return self._item is None and self._count is None

    @property
    def leaf(self):
        """True if this node is a leaf in the tree; false if otherwise."""
        return len(self._children) == 0

    def parent():
        doc = "The node's parent."
        def fget(self):
            return self._parent
        def fset(self, value):
            if value is not None and not isinstance(value, FPNode):
                raise TypeError("A node must have an FPNode as a parent.")
            if value and value.tree is not self.tree:
                raise ValueError("Cannot have a parent from another tree.")
            self._parent = value
        return locals()
    parent = property(**parent())

    def neighbor():
        doc = """
        The node's neighbor; the one with the same value that is "to the right"
        of it in the tree.
        """
        def fget(self):
            return self._neighbor
        def fset(self, value):
            if value is not None and not isinstance(value, FPNode):
                raise TypeError("A node must have an FPNode as a neighbor.")
            if value and value.tree is not self.tree:
                raise ValueError("Cannot have a neighbor from another tree.")
            self._neighbor = value
        return locals()
    neighbor = property(**neighbor())

    @property
    def children(self):
        """The nodes that are children of this node."""
        return tuple(self._children.itervalues())

    def inspect(self, depth=0):
        print ('  ' * depth) + repr(self)
        for child in self.children:
            child.inspect(depth + 1)

    def __repr__(self):
        if self.root:
            return "<%s (root)>" % type(self).__name__
        return "<%s %r (%r)>" % (type(self).__name__, self.item, self.count)


if __name__ == '__main__':
    from optparse import OptionParser
    import csv

    p = OptionParser(usage='%prog data_file')
    p.add_option('-s', '--minimum-support', dest='minsup', type='int',
        help='Minimum itemset support (default: 2)')
    p.add_option('-c', '--minimum-confidence', dest='minconf', type='float',
        help='Minimum confidence (float value in [0, 1], default: 0.5)')
    p.set_defaults(minsup=2)
    p.set_defaults(minconf=0.5)

    options, args = p.parse_args()
    if len(args) < 1:
        p.error('must provide the path to a CSV file to read')

    f = open(args[0])
    start_time =  time.time()
    try:
        for itemset, support, pos_count, confidence, chi_square in find_frequent_itemsets(csv.reader(f), options.minsup, options.minconf, True):
            print '{' + ', '.join(itemset) + '} ' + str(support) + ' ' + str(pos_count) + ' ' + str(confidence) + ' ' + str(chi_square)
    finally:
        f.close()
    elapsed_time =  time.time() - start_time
    print "Elapsed time:", elapsed_time
