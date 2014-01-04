import functools
import irc3
from irc3.plugins.command import command
import irc3_pugbot.pug

COLORS = ['red', 'blue']
PLAYER_MSG = 'You have been picked as {class_} for {color} team.'
TEAM_MSG = '{color} team: {players}'
CLASS_MSG = '{player} on {class_}'


def send_teams_message(privmsg, teams):
    for i, team in enumerate(teams):
        players = ', '.join([CLASS_MSG.format(p, c.title()) for c, p in team.items()])
        team_msg = TEAM_MSG.format(color=COLORS[i].title(), players=players)
        privmsg(team_msg)


def send_unstaged(privmsg, unstaged):
    privmsg('Players added: {0}'.format(', '.join(unstaged.keys())))


@irc3.plugin
class PugBot:
    def __init__(self, bot):
        self.bot = bot
        self.log = self.bot.log
        self.config = self.bot.config['irc3_pugbot']
        self.pug_type = self.config['type']
        self.channel = self.config['channel']
        self.privmsg = functools.partial(self.bot.privmsg, self.channel)
        if self.pug_type == irc3_pugbot.pug.PugType.highlander:
            self.pug = irc3_pugbot.pug.Tf2HighlanderPug()
        elif self.pug_type == irc3_pugbot.pug.PugType.fours:
            self.pug = irc3_pugbot.pug.Tf2FoursPug()
        else:
            raise NotImplementedError

    @irc3.event(irc3.rfc.NEW_NICK)
    def nick(self, mask, channel):
        """Keep pug state in line with nick changes"""
        if mask.nick in self.pug.unstaged_players:
            player_info = self.pug.unstaged_players.pop(mask.nick)
            self.pug.unstaged_players[mask.new_nick] = player_info
        if mask.nick in self.pug.staged_players:
            player_info = self.pug.staged_players.pop(mask.nick)
            self.pug.staged_players[mask.new_nick] = player_info
        if mask.nick in self.pug.captains:
            i = self.pug.captains.index(mask.nick)
            self.pug.captains[i] = mask.new_nick
        if self.pug.teams:
            for team in self.pug.teams:
                for class_, nick in team.items():
                    if mask.nick == nick:
                        team[class_] = mask.new_nick

    def try_stage(self):
        if self.pug.can_stage:
            self.pug.stage()
            team_msg = '{0} - {1}'
            self.privmsg('Captains: {0}'.format(', '.join(team_msg.format(COLORS[i].upper(), self.pug.captains[i]) for i in range(2))))
            self.privmsg('It is {0}\'s turn to pick'.format(self.pug.captains[self.pug.picking_team]))

    @command
    def need(self, mask, target, args):
        """Check what's needed to start the pug"""
        assert target == self.channel
        captain_need_count, player_need_count, class_need_count = self.pug.need
        base_need_msg = 'Need:'
        need_parts = []
        if class_need_count:
            need_parts.extend('{0}: {1}'.format(k, v) for k, v in class_need_count.items())
        if captain_need_count:
            need_parts.append('captain: {0}'.format(captain_need_count))
        if player_need_count:
            need_parts.append('players: {0}'.format(player_need_count))
        need_msg = '{0} {1}'.format(base_need_msg, ', '.join(need_parts))
        self.privmsg(need_msg)

    @command
    def list(self, mask, target, args):
        """List players added to a class"""
        assert target == self.channel
        class_ = args[0].lower()
        assert class_ in self.pug.allowed_classes
        if self.pug.staged_players and mask.nick in self.pug.staged_players:
            players = [p for p, (cs, _) in self.pug.staged_players.items() if class_ in cs]
        else:
            players = [p for p, (cs, _) in self.pug.unstaged_players.items() if class_ in cs]
        self.privmsg('{0}s: {1}'.format(class_, ', '.join(players)))

    @command
    def add(self, mask, target, args):
        """Add yourself to the pug"""
        assert target == self.channel
        classes = set(a.lower() for a in args)
        assert all(c in self.pug.allowed_classes or c == 'captain' for c in classes)
        captain = 'captain' in classes
        classes.remove('captain')
        self.pug.add(mask.nick, classes, captain)
        self.privmsg('Players added: {0}'.format(', '.join(self.pug.unstaged_players.keys())))
        self.try_stage()

    @command
    def remove(self, mask, target, args):
        """Remove yourself from the pug (prior to picking start)"""
        assert target == self.channel
        try:
            self.pug.remove(mask.nick)
        except KeyError:
            pass
        else:
            send_unstaged(self.privmsg, self.pug.unstaged_players)
            if self.staging_task and not self.pug.can_stage():
                self.staging_task.cancel()

    @command
    def turn(self, mask, target, args):
        """See whose turn it is to pick"""
        if self.pug.captains:
            self.privmsg('It is {0}\'s turn to pick'.format(self.pug.captains[self.pug.picking_team]))
        else:
            self.privmsg('No picking happening right now')

    @command
    def pick(self, mask, target, args):
        """Pick player on a class"""
        if self.pug.staged_players is None:
            self.privmsg('{0}, pug is not ready for picking'.format(mask.nick))
        elif mask.nick not in self.pug.captains:
            self.privmsg('{0}, only captains can pick'.format(mask.nick))
        elif mask.nick != self.pug.captains[self.pug.picking_team]:
            self.privmsg('{0}, it is not your pick'.format(mask.nick))
        else:
            self.pug.pick(args[0], args[1].lower())
            if self.pug.can_start:
                teams = self.pug.make_game()
                send_teams_message(self.privmsg, teams)
                for i, team in enumerate(teams):
                    for class_, player in team:
                        self.bot.privmsg(player, PLAYER_MSG.format(class_=class_, team=COLORS[i].title()))
                self.try_stage()
            else:
                self.privmsg('It is {0}\'s turn to pick'.format(self.pug.captains[self.pug.picking_team]))
