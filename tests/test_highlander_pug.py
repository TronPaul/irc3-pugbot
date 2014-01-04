import unittest
import unittest.mock
import itertools
import tests.utils
import irc3_pugbot.pug


class HighlanderPugTest(unittest.TestCase):
    def test_add_any_class(self):
        for c in tests.utils.CLASSES:
            pb = irc3_pugbot.pug.Tf2HighlanderPug()
            pb.add('nick', [c])
            self.assertEquals(len(pb.unstaged_players), 1)
            self.assertEquals(pb.unstaged_players['nick'], ([c], False))

    def test_add_multi_class(self):
        for i in range(0, len(tests.utils.CLASSES)-1, 2):
            pb = irc3_pugbot.pug.Tf2HighlanderPug()
            pb.add('nick', [tests.utils.CLASSES[i], tests.utils.CLASSES[i+1]])
            self.assertEquals(len(pb.unstaged_players), 1)
            self.assertEquals(pb.unstaged_players['nick'], ([tests.utils.CLASSES[i], tests.utils.CLASSES[i+1]], False))

    def test_readd_different_class(self):
        pb = irc3_pugbot.pug.Tf2HighlanderPug()
        for c in tests.utils.CLASSES:
            pb.add('nick', [c])
            self.assertEquals(len(pb.unstaged_players), 1)
            self.assertEquals(pb.unstaged_players['nick'], ([c], False))

    def test_add_captain_with_class(self):
        for c in tests.utils.CLASSES:
            pb = irc3_pugbot.pug.Tf2HighlanderPug()
            pb.add('nick', [c], True)
            self.assertEquals(len(pb.unstaged_players), 1)
            self.assertEquals(pb.unstaged_players['nick'], ([c], True))

    def test_captain_fails_without_class(self):
        pb = irc3_pugbot.pug.Tf2HighlanderPug()
        self.assertRaises(irc3_pugbot.pug.MissingClassError, pb.add, 'nick', [], True)
        self.assertEquals(len(pb.unstaged_players), 0)

    def test_remove(self):
        pb = irc3_pugbot.pug.Tf2HighlanderPug()
        pb.add('nick', [tests.utils.CLASSES[0]])
        pb.remove('nick')
        self.assertEquals(len(pb.unstaged_players), 0)

    def test_remove_without_add_raises_error(self):
        pb = irc3_pugbot.pug.Tf2HighlanderPug()
        self.assertRaises(KeyError, pb.remove, 'nick')

    def test_simple_can_stage(self):
        pb = irc3_pugbot.pug.Tf2HighlanderPug()
        for player in itertools.chain.from_iterable(tests.utils.generate_highlander_game()):
            pb.add(player.nick, player.classes, True)
        self.assertTrue(pb.can_stage)

    def test_simple_need(self):
        pb = irc3_pugbot.pug.Tf2HighlanderPug()
        for player in itertools.chain.from_iterable(tests.utils.generate_highlander_game()):
            pb.add(player.nick, player.classes, True)
        self.assertEquals(pb.need, (0, 0, {}))

    def test_need_captains(self):
        pb = irc3_pugbot.pug.Tf2HighlanderPug()
        for player in itertools.chain.from_iterable(tests.utils.generate_highlander_game()):
            pb.add(player.nick, player.classes)
        self.assertEquals(pb.need, (2, 0, {}))

    def test_empty_need(self):
        pb = irc3_pugbot.pug.Tf2HighlanderPug()
        self.assertEquals(pb.need, (2, 18, {c: 2 for c in tests.utils.CLASSES}))

    def test_cannot_stage_without_two_captains(self):
        pb = irc3_pugbot.pug.Tf2HighlanderPug()
        for player in itertools.chain.from_iterable(tests.utils.generate_highlander_game()):
            pb.add(player.nick, player.classes)
        self.assertFalse(pb.can_stage)

    def test_cannot_stage_without_two_of_each_class(self):
        pb = irc3_pugbot.pug.Tf2HighlanderPug()
        for player in list(itertools.chain.from_iterable(tests.utils.generate_highlander_game()))[:-2]:
            pb.add(player.nick, player.classes)
        self.assertFalse(pb.can_stage)

    def test_random_captains(self):
        captains = irc3_pugbot.pug.random_captains({'a': ([], True), 'b': ([], True)})
        self.assertEquals(len(captains), 2)
        self.assertTrue('a' in captains)
        self.assertTrue('b' in captains)

    @unittest.mock.patch('irc3_pugbot.pug.random_captains')
    def test_stage(self, random_captains):
        pb = irc3_pugbot.pug.Tf2HighlanderPug()
        players = list(itertools.chain.from_iterable(tests.utils.generate_highlander_game()))
        for player in players:
            pb.add(player.nick, player.classes, True)
        captains = [players[0][0], players[1][0]]
        random_captains.return_value = captains
        pb.stage()
        self.assertFalse(captains[0] in pb.staged_players)
        self.assertFalse(captains[1] in pb.staged_players)
        self.assertEquals(pb.captains, captains)
        self.assertEquals(pb.teams[0], {})
        self.assertEquals(pb.teams[1], {})
        self.assertEquals(pb.picking_team, 0)

    def test_river(self):
        river = irc3_pugbot.pug.river()
        self.assertEquals(0, next(river))
        self.assertEquals(1, next(river))
        self.assertEquals(1, next(river))
        self.assertEquals(0, next(river))
        self.assertEquals(0, next(river))

    @unittest.mock.patch('irc3_pugbot.pug.random_captains')
    def test_simple_pick(self, random_captains):
        pb = irc3_pugbot.pug.Tf2HighlanderPug()
        players = list(itertools.chain.from_iterable(tests.utils.generate_highlander_game()))
        for player in players:
            pb.add(player.nick, player.classes, True)
        random_captains.return_value = [players[0][0], players[1][0]]
        pb.stage()
        pb.pick(players[2][0], 'scout')
        self.assertEquals(pb.teams[0], {'scout': players[2][0]})
        self.assertFalse(players[2][0] in pb.staged_players)
        self.assertEquals(pb.picking_team, 1)

    @unittest.mock.patch('irc3_pugbot.pug.random_captains')
    def test_cannot_pick_class_twice(self, random_captains):
        pb = irc3_pugbot.pug.Tf2HighlanderPug()
        players = list(itertools.chain.from_iterable(tests.utils.generate_highlander_game()))
        for player in players:
            pb.add(player.nick, player.classes, True)
        random_captains.return_value = [players[0][0], players[1][0]]
        pb.stage()
        pb.pick(players[2][0], 'scout')
        self.assertEquals(pb.teams[0], {'scout': players[2][0]})
        pb.pick(players[3][0], 'scout')
        self.assertRaises(irc3_pugbot.pug.ClassAlreadyPickedError, pb.pick, players[4][0], 'scout')

    def test_can_start_highlander(self):
        teams = [{tests.utils.CLASSES[j]: 'nick{0}{1}'.format(i, j) for j in range(8)} for i in range(2)]
        self.assertTrue(irc3_pugbot.pug.can_start_highlander(teams))

    @unittest.mock.patch('irc3_pugbot.pug.random_captains')
    def test_make_game(self, random_captains):
        pb = irc3_pugbot.pug.Tf2HighlanderPug()
        players = []

        def my_order():
            yield 0
            yield 1
            yield from irc3_pugbot.pug.river()

        order = my_order()
        for i, c in enumerate(tests.utils.CLASSES):
            player1 = ('nick{0}{1}'.format(next(order), i), [c])
            player2 = ('nick{0}{1}'.format(next(order), i), [c])
            players.append(player1)
            players.append(player2)
            pb.add(player1[0], player1[1], True)
            pb.add(player2[0], player2[1], True)
        random_captains.return_value = [players[0][0], players[1][0]]
        pb.stage()
        for (i, (nick, classes)) in enumerate(players[2:]):
            pb.pick(nick, classes[0])
        expected_teams = [{tests.utils.CLASSES[j]: 'nick{0}{1}'.format(i, j) for j in range(9)} for i in range(2)]
        teams = pb.make_game()
        self.assertEquals(teams, expected_teams)
        self.assertTrue(pb.captains is None)
        self.assertTrue(pb.staged_players is None)
        self.assertTrue(pb.order is None)
        self.assertTrue(pb.picking_team is None)

    @unittest.mock.patch('irc3_pugbot.pug.random_captains')
    def test_make_game_moves_unpicked_to_unstanged(self, random_captains):
        pb = irc3_pugbot.pug.Tf2HighlanderPug()
        players = []

        def my_order():
            yield 0
            yield 1
            yield from irc3_pugbot.pug.river()

        order = my_order()
        for i, c in enumerate(tests.utils.CLASSES):
            player1 = ('nick{0}{1}'.format(next(order), i), [c])
            player2 = ('nick{0}{1}'.format(next(order), i), [c])
            players.append(player1)
            players.append(player2)
            pb.add(player1[0], player1[1], True)
            pb.add(player2[0], player2[1], True)
        pb.add('unpicked1', [tests.utils.CLASSES[1]])
        pb.add('unpicked2', [tests.utils.CLASSES[2]])
        random_captains.return_value = [players[0][0], players[1][0]]
        pb.stage()
        for (i, (nick, classes)) in enumerate(players[2:]):
            pb.pick(nick, classes[0])
        expected_teams = [{tests.utils.CLASSES[j]: 'nick{0}{1}'.format(i, j) for j in range(9)} for i in range(2)]
        teams = pb.make_game()
        self.assertEquals(teams, expected_teams)
        self.assertTrue(pb.captains is None)
        self.assertTrue(pb.staged_players is None)
        self.assertTrue(pb.order is None)
        self.assertTrue(pb.picking_team is None)
        self.assertEquals(pb.unstaged_players, {'unpicked1': ([tests.utils.CLASSES[1]], False), 'unpicked2': ([tests.utils.CLASSES[2]], False)})
